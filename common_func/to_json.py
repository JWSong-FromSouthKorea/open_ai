from sqlalchemy.ext.declarative import DeclarativeMeta
import sqlalchemy.orm.state
import ujson


def to_json(orm_object: sqlalchemy.orm.state.InstanceState):
    if isinstance(orm_object.__class__, DeclarativeMeta):
        # SQLAlchemy ORM object
        fields = {}
        for field in [x for x in dir(orm_object) if not x.startswith('_') and x != 'metadata']:
            data = orm_object.__getattribute__(field)
            try:
                ujson.dumps(data)  # this will fail on non-encodable values, like other classes
                fields[field] = data
            except TypeError:
                fields[field] = None
        # a json-encodable dict
        return fields
    return orm_object
