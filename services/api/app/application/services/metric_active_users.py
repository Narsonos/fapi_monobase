import app.application.repositories as irepo
import app.application.interfaces as iapp
import logging, datetime as dt
logger = logging.getLogger('app')


class MetricActiveUsersService:
    def __init__(self, repo: irepo.IMetricActiveUsersStorage):
        self.repo = repo

    async def register_activity(self, user_id):
        await self.repo.register_activity(user_id)
    
    async def count_activity(self, timespan: dt.timedelta | int, cleanup: bool = False):
        """
        Returns metric value according to the stored set of user IDs
        - **Timespan** refres to the period of activity you want to get the value for.
          **Timespan** can set as either timedelta or int (seconds)
        - Use **cleanup** argument on the broadest metric only. 
          For example, if you want to get data about Daily Users (last 24h) and Active Now (last 1h),
          You must only set cleanup=True only for the 24h metric. If vice versa, your storage would 
          store only 1h of data, thus making it impossible to provide data for daily activity.
        """
        if isinstance(timespan, dt.timedelta):
            timespan = timespan.total_seconds()
        if cleanup:
            await self.repo.remove_old(timespan_sec=timespan)
        count = await self.repo.get_active_count(timespan_sec=timespan)
        return count
 