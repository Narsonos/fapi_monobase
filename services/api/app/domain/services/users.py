#Pass eq conditions as kwargs. Only valid fields accepted!
#async def get_users(db_session: AsyncSession, **kwargs) -> ScalarResult[models.User]:
#    query = select(models.User)
#    for requested_field,value in kwargs.items():
#        if requested_field in models.User.__fields__: #if field is valid for User model
#            query = query.where(getattr(models.User,requested_field) == value)
#        else:
#            raise exc.CustomDatabaseException(f'"{requested_field}" field does not exist in table User')
#        
#    users = await db_session.scalars(query)
#    return users 