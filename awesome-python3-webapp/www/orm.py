__author__ = "MIS_GDK"
"""
对象关系映射：通俗说就是将一个数据库表映射为一个类
"""
import asyncio
import logging
import aiomysql


def log(sql, args=()):
    logging.info("SQL:%s" % sql)


# 异步协程：创建数据库连接池
async def create_pool(loop, **kw):
    logging.info("create database connection pool")
    # 全局私有变量，内部可以访问
    global __pool
    __pool = await aiomysql.create_pool(
        # kw.get(key,default)：通过key在kw中查找对应的value，如果没有则返回默认值default
        host=kw.get("host", "localhost"),
        port=kw.get("port", 3306),
        user=kw["user"],
        password=kw["password"],
        db=kw["db"],
        charset=kw.get("charset", "utf8"),
        autocommit=kw.get("autocommit", True),
        maxsize=kw.get("maxsize", 10),
        minsize=kw.get("minsize", 1),
        loop=loop,
    )


# 协程：销毁所有的数据库连接池
async def destory_pool():
    global __pool
    if __pool is not None:
        __pool.close()
        await __pool.wait_closed()


# 协程：面向sql的查询操作:size指定返回的查询结果数
async def select(sql, args, size=None):
    log(sql)
    global __pool
    # 异步等待连接池对象返回可以连接线程，with语句则封装了清理（关闭conn）和处理异常的工作
    async with __pool.get() as conn:
        # 查询需要返回查询的结果，按照dict返回，所以游标cursor中传入了参数aiomysql.DictCursor
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # 将sql中的'?'替换为'%s'，因为mysql语句中的占位符为%s
            await cur.execute(sql.replace("?", "%s"), args)
            if size:
                rs = await cur.fetchmany(size)
            else:
                rs = await cur.fetchall()

        logging.info("rows returned: %s" % len(rs))
        return rs


# 将面向mysql的增insert、删delete、改update封装成一个协程
# 语句操作参数一样，直接封装成一个通用的执行函数
# 返回受影响的行数
async def execute(sql, args, autocommit=True):
    log(sql)
    async with __pool.get() as conn:
        # 若设置不是自动提交，则手动开启事务
        if not autocommit:
            await conn.begin()
        try:
            # 打开一个DictCursor，它与普通游标的不同在于，以dict形式返回结果
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql.replace("?", "%s"), args)
                affected = cur.rowcount
            # 同上, 如果设置不是自动提交的话，手动提交事务
            if not autocommit:
                await conn.commit
        except BaseException as e:
            # 出错, 回滚事务到增删改之前
            if not autocommit:
                await conn.rollback()
            raise
        return affected


# 查询字段计数：替换成sql识别的'？'
# 根据输入的字段生成占位符列表
def create_args_string(num):
    L = []
    for n in range(num):
        L.append("?")
    return ",".join(L)


# 定义Field类，保存数据库中表的字段名和字段类型
class Field(object):
    # 表的字段包括：名字、类型、是否为主键、默认值
    def __init__(self, name, column_type, primary_key, default):
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        self.default = default

    # 打印数据库中的表时，输出表的信息：类名、字段名、字段类型
    def __str__(self):
        return "<%s, %s:%s>" % (self.__class__.__name__, self.column_type, self.name)


# 定义不同类型的衍生Field
# 表的不同列的字段的类型不同
class StringField(Field):
    def __init__(self, name=None, primary_key=False, default=None, ddl="varchar(100)"):
        super().__init__(name, ddl, primary_key, default)


class BooleanField(Field):
    def __init__(self, name=None, default=False):
        super().__init__(name, "boolean", False, default)


class IntegerField(Field):
    def __init__(self, name=None, primary_key=False, default=0):
        super().__init__(name, "bigint", primary_key, default)


class FloatField(Field):
    def __init__(self, name=None, primary_key=False, default=0.0):
        super().__init__(name, "real", primary_key, default)


class TextField(Field):
    def __init__(self, name=None, default=None):
        super().__init__(name, "text", False, default)


# metaclass是类的模板，所以必须从`type`类型派生：
# 定义Model的metaclass元类
# 所有的元类都继承自type
# ModelMetaclass元类定义了所有Model基类（继承ModelMetaclass）的子类实现的操作

# -*-ModelMetaclass：为一个数据库表映射成一个封装的类做准备
# 读取具体子类(eg：user)的映射信息
# 创造类的时候，排除对Model类的修改
# 在当前类中查找所有的类属性(attrs),如果找到Field属性，就保存在__mappings__的dict里，
# 同时从类属性中删除Field（防止实例属性覆盖类的同名属性）
# __table__保存数据库表名
class ModelMetaclass(type):
    # __new__控制__init__的执行，所以在其执行之前
    # cls：代表要__init__的类，此参数在实例化时由python解释器自动提供（eg：下文的User、Model)
    # bases:代表继承父类的集合
    # attrs:类的方法集合
    def __new__(cls, name, bases, attrs):
        if name == "Model":
            return type.__new__(cls, name, bases, attrs)
        tableName = attrs.get("__table__", None) or name

        logging.info("found model: %s (table: %s)" % (name, tableName))
        mappings = dict()
        fields = []

        primaryKey = None
        for k, v in attrs.items():
            if isinstance(v, Field):
                logging.info("found mapping: %s ==> %s" % (k, v))
                mappings[k] = v
                if v.primary_key:
                    # 找到主键:
                    if primaryKey:
                        raise StandardError("Duplicate primary key for field: %s" % k)
                    primaryKey = k
                else:
                    fields.append(k)

        if not primaryKey:
            raise StandardError("Primary key not found.")

        for k in mappings.keys():
            attrs.pop(k)

        escaped_fields = list(map(lambda f: "`%s`" % f, fields))
        attrs["__mappings__"] = mappings  # 保存属性和列的映射关系
        attrs["__table__"] = tableName
        attrs["__primary_key__"] = primaryKey  # 主键属性名
        attrs["__fields__"] = fields  # 除主键外的属性名
        attrs["__select__"] = "select `%s`, %s from `%s`" % (
            primaryKey,
            ", ".join(escaped_fields),
            tableName,
        )
        attrs["__insert__"] = "insert into `%s` (%s, `%s`) values (%s)" % (
            tableName,
            ", ".join(escaped_fields),
            primaryKey,
            create_args_string(len(escaped_fields) + 1),
        )
        attrs["__update__"] = "update `%s` set %s where `%s`=?" % (
            tableName,
            ", ".join(map(lambda f: "`%s`=?" % (mappings.get(f).name or f), fields)),
            primaryKey,
        )
        attrs["__delete__"] = "delete from `%s` where `%s`=?" % (tableName, primaryKey)
        return type.__new__(cls, name, bases, attrs)


class Model(dict, metaclass=ModelMetaclass):
    def __init__(self, **kw):
        super(Model, self).__init__(**kw)

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Model' object has no attribute '%s'" % key)

    def __setattr__(self, key, value):
        self[key] = value

    def getValue(self, key):
        return getattr(self, key, None)

    def getValueOrDefault(self, key):
        value = getattr(self, key, None)
        if value is None:
            field = self.__mappings__[key]
            if field.default is not None:
                value = field.default() if callable(field.default) else field.default
                logging.debug("using default value for %s: %s" % (key, str(value)))
                setattr(self, key, value)
        return value

    @classmethod
    async def findAll(cls, where=None, args=None, **kw):

        " find objects by where clause. "
        sql = [cls.__select__]
        if where:
            sql.append("where")
            sql.append(where)
        if args is None:
            args = []
        orderBy = kw.get("orderBy", None)
        if orderBy:
            sql.append("order by")
            sql.append(orderBy)
        limit = kw.get("limit", None)
        if limit is not None:
            sql.append("limit")
            if isinstance(limit, int):
                sql.append("?")
                args.append(limit)
            elif isinstance(limit, tuple) and len(limit) == 2:
                sql.append("?, ?")
                args.extend(limit)
            else:
                raise ValueError("Invalid limit value: %s" % str(limit))
        rs = await select(" ".join(sql), args)
        return [cls(**r) for r in rs]

    @classmethod
    async def findNumber(cls, selectField, where=None, args=None):
        " find number by select and where. "
        sql = ["select %s _num_ from `%s`" % (selectField, cls.__table__)]
        if where:
            sql.append("where")
            sql.append(where)
        rs = await select(" ".join(sql), args, 1)
        if len(rs) == 0:
            return None
        return rs[0]["_num_"]

    @classmethod
    async def find(cls, pk):
        " find object by primary key. "
        rs = await select(
            "%s where `%s`=?" % (cls.__select__, cls.__primary_key__), [pk], 1
        )
        if len(rs) == 0:
            return None
        return cls(**rs[0])

    async def save(self):
        args = list(map(self.getValueOrDefault, self.__fields__))
        args.append(self.getValueOrDefault(self.__primary_key__))
        rows = await execute(self.__insert__, args)
        if rows != 1:
            logging.warn("failed to insert record: affected rows: %s" % rows)

    async def update(self):
        args = list(map(self.getValue, self.__fields__))
        args.append(self.getValue(self.__primary_key__))
        rows = await execute(self.__update__, args)
        if rows != 1:
            logging.warn("failed to update by primary key: affected rows: %s" % rows)

    async def remove(self):
        args = [self.getValue(self.__primary_key__)]
        rows = await execute(self.__delete__, args)
        if rows != 1:
            logging.warn("failed to remove by primary key: affected rows: %s" % rows)
