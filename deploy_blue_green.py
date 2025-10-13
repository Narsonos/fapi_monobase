import subprocess, json, os, time, typing as t, argparse, re, asyncio, sys, dataclasses as dc, pathlib
import traceback, collections as c

parser = argparse.ArgumentParser()
parser.add_argument("--project_name", type=str, required=True, help="Specifies project name")
args=parser.parse_args()


@dc.dataclass
class TargetService:
    name: str
    is_upstream: bool


@dc.dataclass
class DeploymentConfig:
    project_name: str
    compose_path: pathlib.Path
    upstream_conf: pathlib.Path
    env_path: pathlib.Path | None
    services: list[TargetService]

    @staticmethod
    def from_json(path: str, default_project_name: t.Optional[str] = None) -> "DeploymentConfig":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # подставляем project_name, если его нет
        if "project_name" not in data and default_project_name:
            data["project_name"] = default_project_name

        # преобразуем в объекты
        data["compose_path"] = pathlib.Path(data["compose_path"])
        data["upstream_conf"] = pathlib.Path(data["upstream_conf"])
        if data.get("env_path"):
            data["env_path"] = pathlib.Path(data["env_path"])

        data["services"] = [TargetService(**s) for s in data.get("services", [])]

        return DeploymentConfig(**data)


class CommandFailed(Exception):
    def __init__(self, command, code, stderr):
        self.command = command
        self.code = code
        self.stderr = stderr
        super().__init__(f'Error occured while executing: {command}.\nExit code: {code}\nStderr: {stderr}')    

class ManualStop(Exception):
    '''Raised when the code considers the situation as an error and wants to shutdown'''



class DeploymentJob:
    def __init__(self, deploy_json_path='./deploy.json'):
        self.config = None
        with open(deploy_json_path, 'r') as f:
            self.config = DeploymentConfig.from_json(deploy_json_path, args.project_name)
        
        self.current_color = None
        self.next_color = 'blue'

        self.containers_before = {c for c in self.project_containers}

        self.nginx_container_name = self.find_container_by_keyword('nginx')
        self.request_rollback_event = asyncio.Event()

        if self.nginx_container_name:
            print(f'[Nginx] Container detected: {self.nginx_container_name}')
        else:
            self.nginx_container_name = f'{self.config.project_name}-nginx-1'
            print(f'[Nginx] No container detected. Assuming nginx is: {self.nginx_container_name}')
            

        if self.project_containers:
            self.current_color = self.find_current_color(self.config.services[0].name)

        if self.current_color == 'both':
            print(f'[Deploy: Error] Found both colors existing. Container list: {self.project_containers}\nCannot deploy properly. Exiting.')
            return 
        
        if self.current_color == 'blue':
            self.next_color = 'green'

        print(f'[Deploy] Strategy: {"No color" if self.current_color is None else self.current_color} ---starting---> {self.next_color}')
        try:
            self.deploy_sequence()
        except (CommandFailed, ManualStop) as e:
            print(e)
            self.rollback_and_exit()
        

    def rollback_and_exit(self):
        print('[Rollback] Rollback. Cleaning up and exiting...')
        self.request_rollback_event.set()
        created_by_this_script = set(self.project_containers) - self.containers_before
        print(f'[Rollback] These containers ({len(created_by_this_script)}) are considered as created by the script:')
        if not created_by_this_script:
            print(f'No containers...')
        else:
            for c in created_by_this_script:
                print(f' - {c}')
            for c in created_by_this_script:
                self.rm(c, force=True)
        os._exit(1)



    @staticmethod
    def run(command):
        """
        Выполняет команду, печатая её вывод в реальном времени,
        и захватывает его для возврата.
        """
        # shell=True оставлен для совместимости с вашим кодом,
        # но безопаснее передавать команду списком и убрать shell=True.
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, 
            shell=True,
            text=True,
            encoding='utf-8'
        )

        captured_lines = []
        for line in process.stdout:
            sys.stdout.write(line)
            captured_lines.append(line) 

        process.wait()
        returncode = process.returncode

        captured_output = "".join(captured_lines)

        if returncode != 0:
            raise CommandFailed(command, returncode, captured_output)

        Result = c.namedtuple('Result', ['stdout', 'returncode'])
        return Result(stdout=captured_output, returncode=returncode)



    @staticmethod
    def rm(container_name, force=False):
        if force:
            DeploymentJob.run(f'docker rm --force {container_name}')
        else:
            DeploymentJob.run(f"docker stop {container_name}")
            DeploymentJob.run(f"docker rm {container_name}")
        print(f'[Cleaner] Container "{container_name}" was removed!')
        
    @property
    def project_containers(self):
        res = DeploymentJob.run('docker ps -a --format {{.Names}}')
        return [c for c in res.stdout.splitlines() if c.startswith(self.config.project_name)]
    

    def filter_service_containers(self, service):
        return [c for c in self.project_containers if service in c.lstrip(self.config.project_name+'-')]

    def find_current_color(self, service) -> t.Literal["blue","green","none","both"]:
        if f'{self.config.project_name}-{service}_blue' in self.project_containers:
            self.current_color = 'blue'
        if f'{self.config.project_name}-{service}_green' in self.project_containers:
            self.current_color = 'both' if self.current_color else 'green'
        self.current_color  = self.current_color if self.current_color else 'none'
        return self.current_color


    def add_alias_to_all_container_networks(self, service):
        full_container_name = f'{self.config.project_name}-{service}_{self.next_color}'
        rs = DeploymentJob.run(['docker', 'inspect', full_container_name, '--format={{json .NetworkSettings.Networks}}'])
        nets = json.loads(rs.stdout.strip())
        for net in nets:
            print(f'[Deploy: networks] Reconnecting {full_container_name} to {net} with alias {service}_{self.next_color}')
            DeploymentJob.run(f'docker network disconnect {net} {full_container_name}')
            DeploymentJob.run(f'docker network connect {net} {full_container_name} --alias {service}_{self.next_color}')

    def find_latest_scale(self, service):
        for c in self.project_containers:
            if m := re.match(rf'{self.config.project_name}-{service}-(\d+)', c):
                return m[0]


    async def wait_and_rename_single_service(self, service, retries=15, interval_s=4):
        container_name = self.find_latest_scale(service)

        if not container_name:
            raise ManualStop(f'New instnace of service "{service}" did not boot properly -> Cancelling.')
            
        for _ in range(retries):
            if self.request_rollback_event.is_set():
                return 
            
            result = self.run(f"docker inspect --format='{{.State.Health.Status}}' {container_name}")
            status = result.stdout.strip().lower()
            if status == 'healthy':
                break
            await asyncio.sleep(interval_s)
        else:
            raise ManualStop(f"App container {container_name} failed to become healthy")
        new_name = f'{self.config.project_name}-{service}_{self.next_color}'
        self.run(f'docker rename {container_name} "{new_name}"')
        self.add_alias_to_all_container_networks(service)

    async def wait_and_rename_all_services(self):
        try:
            await asyncio.gather(*(self.wait_and_rename_single_service(s.name) for s in self.config.services))
        except Exception as e:
            print('-'*10 + 'asyncio.gather Exception' + '-'*10)
            traceback.print_exc()
            print('-'*40)
            raise

    def run_new_app(self, build_whole_compose=False):
        if build_whole_compose:
            DeploymentJob.run(f'docker compose {f"--env-file {self.config.env_path}" if self.config.env_path else None} -f {self.config.compose_path} up -d --build --no-recreate')
        else:
            services_sub = ''
            scale_sub = ''
            for service in self.config.services:
                services_sub += f'{service.name} '
                scale_sub += f'--scale {service.name}=2 '
            command = f'docker compose {f"--env-file {self.config.env_path}" if self.config.env_path else None} -f {self.config.compose_path} up {services_sub.strip()} -d --no-recreate {scale_sub.strip()}'
            DeploymentJob.run(command)
        asyncio.run(self.wait_and_rename_all_services())

            
    def rewrite_nginx(self):
        names_mapping = {}
        if self.current_color in ['blue','green']:
            color = self.current_color
        else:
            color = ''
        print('[Nginx] Rewriting nginx using the following mapping:')        
        for service in self.config.services:
            if service.is_upstream:
                names_mapping[f'{service.name}{f"_{color}" if color else ""}'] = f'{service.name}_{self.next_color}'
                print(f'{service.name}{f"_{color}" if color else ""} -> {service.name}_{self.next_color}')
    
        def replacer(match):
            prefix, name, suffix = match.groups()
            new_name = names_mapping.get(name, name)  
            return f"{prefix}{new_name}{suffix}"
        
        with open(self.config.upstream_conf, 'r+') as conf:
            backup = conf.read()
            content = re.sub(r'(server )([\w-]+)(:)', replacer, backup)
            conf.seek(0)
            conf.write(content)
            conf.truncate()
            print('[Nginx] Reloading nginx...')   
            try:
                self.run(f'docker exec {self.nginx_container_name} nginx -s reload')
            except CommandFailed:
                print('[Nginx] Reload failed. Restoring nginx upstream.conf content')
                conf.truncate(0)
                conf.seek(0)
                conf.write(backup)
                raise


    def find_container_by_keyword(self, kw):
        for c in self.project_containers:
            if kw in c:
                return c


    def deploy_sequence(self):
        if self.current_color is None:
            build_whole_compose = True
        else:
            build_whole_compose = False

        self.run_new_app(build_whole_compose=build_whole_compose)
        self.rewrite_nginx()
        if self.current_color:
            for service in self.config.services:
                self.rm(f'{self.config.project_name}-{service.name}_{self.current_color}')
        print("[Deploy] Deployment has been executed successfully!")
        os._exit(1)



def main():
    job = DeploymentJob(deploy_json_path='deploy_blue_green.conf.json')

if __name__ == '__main__':
    main()