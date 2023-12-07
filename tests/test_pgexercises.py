import pytest
import psycopg2
import time

from datetime import datetime

DATABASE_NAME = "test_exercises"


@pytest.fixture(scope="module")
def clubdata_ddl():
    with open("./tests/pgexercises_data/clubdata_ddl.sql", "r") as f:
        return f.read()


@pytest.fixture(scope="module")
def clubdata_data():
    with open("./tests/pgexercises_data/clubdata_data.sql", "r") as f:
        return f.read()


@pytest.fixture(scope="module")
def exercises_database():
    conn = psycopg2.connect(host="localhost", port=5433, database="postgres", user="yugabyte")
    conn.set_session(autocommit=True)
    cursor = conn.cursor()
    try:
        cursor.execute(f"DROP DATABASE IF EXISTS {DATABASE_NAME}")
        cursor.execute(f"CREATE DATABASE {DATABASE_NAME}")
        yield None
    except:
        ...
    finally:
        conn.set_session(autocommit=True)
        cursor.execute(f"DROP DATABASE {DATABASE_NAME}")
        cursor.close()
        conn.close()


@pytest.fixture(scope="module")
def connection(exercises_database, clubdata_ddl, clubdata_data):
    conn = psycopg2.connect(host="localhost", port=5433, database=DATABASE_NAME, user="yugabyte")

    conn.set_session(autocommit=True)
    cursor = conn.cursor()
    cursor.execute(clubdata_ddl)
    cursor.execute(clubdata_data)
    cursor.close()
    conn.set_session(autocommit=False)

    try:
        yield conn
    except:
        ...
    finally:
        conn.close()


@pytest.fixture(autouse=True)
def slow_down_tests():
    yield
    time.sleep(1)


def test_basic_1(connection):
    with connection.cursor() as cursor:
        cursor.execute("select * from cd.facilities order by facid")
        data = cursor.fetchall()
        assert len(data) == 9
        assert data[0] == (0, "Tennis Court 1", 5, 25, 10000, 200)


def test_basic_2(connection):
    with connection.cursor() as cursor:
        cursor.execute("select name, membercost from cd.facilities order by facid")
        data = cursor.fetchall()
        assert len(data) == 9
        assert data[0] == ("Tennis Court 1", 5)


def test_basic_3(connection):
    with connection.cursor() as cursor:
        cursor.execute("select * from cd.facilities where membercost != 0 order by facid")
        data = cursor.fetchall()
        assert len(data) == 5
        assert data[-1] == (6, "Squash Court", 3.5, 17.5, 5000, 80)


def test_basic_4(connection):
    with connection.cursor() as cursor:
        cursor.execute(
            "select facid, name, membercost, monthlymaintenance from cd.facilities where membercost != 0 and 50 *"
            " membercost < monthlymaintenance order by facid"
        )
        data = cursor.fetchall()
        assert len(data) == 2
        assert data[0] == (4, "Massage Room 1", 35, 3000)
        assert data[1] == (5, "Massage Room 2", 35, 3000)


def test_basic_5(connection):
    with connection.cursor() as cursor:
        cursor.execute("select * from cd.facilities where name like '%Tennis%' order by facid")
        data = cursor.fetchall()
        assert len(data) == 3
        assert data[0] == (0, "Tennis Court 1", 5, 25, 10000, 200)


def test_basic_6(connection):
    with connection.cursor() as cursor:
        cursor.execute("select * from cd.facilities where facid in (1,5) order by facid")
        data = cursor.fetchall()
        assert len(data) == 2
        assert data[0] == (1, "Tennis Court 2", 5, 25, 8000, 200)


def test_basic_7(connection):
    with connection.cursor() as cursor:
        cursor.execute(
            "select name,"
            "case when (monthlymaintenance > 100) then"
            "    'expensive'"
            "else"
            "    'cheap'"
            "end as cost "
            "from cd.facilities order by facid"
        )
        data = cursor.fetchall()
        assert len(data) == 9
        assert data[0] == ("Tennis Court 1", "expensive")
        assert len([row for row in data if row[1] == "cheap"]) == 5


def test_basic_8(connection):
    with connection.cursor() as cursor:
        cursor.execute(
            "select memid, surname, firstname, joindate from cd.members "
            "where joindate >= '2012-09-01'::date order by memid"
        )
        data = cursor.fetchall()
        assert len(data) == 10
        assert data[0] == (24, "Sarwin", "Ramnaresh", datetime(2012, 9, 1, 8, 44, 42))


def test_basic_9(connection):
    with connection.cursor() as cursor:
        cursor.execute("select distinct surname from cd.members order by surname limit 10")
        data = cursor.fetchall()
        assert len(data) == 10
        assert data == [
            ("Bader",),
            ("Baker",),
            ("Boothe",),
            ("Butters",),
            ("Coplin",),
            ("Crumpet",),
            ("Dare",),
            ("Farrell",),
            ("GUEST",),
            ("Genting",),
        ]


def test_basic_10(connection):
    with connection.cursor() as cursor:
        cursor.execute("select name from cd.facilities union select surname from cd.members")
        data = cursor.fetchall()
        assert len(data) == 34
        assert ("Bader",) in data
        assert ("Tennis Court 1",) in data


def test_basic_11(connection):
    with connection.cursor() as cursor:
        cursor.execute("select max(joindate) from cd.members")
        data = cursor.fetchall()
        assert len(data) == 1
        assert data[0] == (datetime(2012, 9, 26, 18, 8, 45),)


def test_basic_12(connection):
    with connection.cursor() as cursor:
        cursor.execute(
            "select firstname, surname, joindate from cd.members "
            " where joindate = (select max(joindate) from cd.members)"
        )
        data = cursor.fetchall()
        assert len(data) == 1
        assert data[0] == (
            "Darren",
            "Smith",
            datetime(2012, 9, 26, 18, 8, 45),
        )


def test_join_1(connection):
    with connection.cursor() as cursor:
        cursor.execute(
            "select starttime from cd.members join cd.bookings on members.memid = bookings.memid "
            "where members.firstname = 'David' and members.surname = 'Farrell' order by starttime"
        )
        data = cursor.fetchall()
        assert len(data) == 34
        assert data[0] == (datetime(2012, 9, 18, 9, 0, 0),)
        assert data[-1] == (datetime(2012, 9, 30, 14, 30, 0),)


def test_join_2(connection):
    with connection.cursor() as cursor:
        cursor.execute(
            "select starttime as start, name from cd.facilities inner join cd.bookings on facilities.facid ="
            " bookings.facid where starttime >= '2012-09-21' and starttime < '2012-09-22' and name like '%Tennis"
            " Court%' order by start "
        )
        data = cursor.fetchall()
        assert len(data) == 12
        assert data[0] == (datetime(2012, 9, 21, 8, 0, 0), "Tennis Court 1")
        assert data[1] == (datetime(2012, 9, 21, 8, 0, 0), "Tennis Court 2")
        assert data[-1] == (datetime(2012, 9, 21, 18, 0, 0), "Tennis Court 2")


def test_join_3(connection):
    with connection.cursor() as cursor:
        cursor.execute(
            "select distinct first.firstname as firstname, first.surname as surname "
            "from cd.members first inner join cd.members second on first.memid = second.recommendedby "
            "order by surname, firstname"
        )
        data = cursor.fetchall()
        assert len(data) == 13
        assert data[0] == ("Florence", "Bader")
        assert data[1] == ("Timothy", "Baker")


def test_join_4(connection):
    with connection.cursor() as cursor:
        cursor.execute(
            "select mem.firstname as memfname, mem.surname as memsname, rec.firstname as recfname, rec.surname as"
            " recsname from cd.members mem left join cd.members rec on mem.recommendedby = rec.memid order by memsname,"
            " memfname"
        )
        data = cursor.fetchall()
        assert len(data) == 31
        assert data[0] == ("Florence", "Bader", "Ponder", "Stibbons")
        assert data[1] == ("Anne", "Baker", "Ponder", "Stibbons")
        assert data[-2] == ("Hyacinth", "Tupperware", None, None)


def test_join_5(connection):
    with connection.cursor() as cursor:
        cursor.execute(
            "select distinct mem.firstname || ' ' || mem.surname as member, x.name as facility  from cd.members mem"
            " join (cd.bookings bks join cd.facilities fac on bks.facid = fac.facid) x on mem.memid = x.memid where"
            " x.name like 'Tennis Court%' order by member, facility"
        )
        data = cursor.fetchall()
        assert len(data) == 46
        assert data[0] == ("Anne Baker", "Tennis Court 1")
        assert data[1] == ("Anne Baker", "Tennis Court 2")
        assert data[-1] == ("Tracy Smith", "Tennis Court 2")


def test_join_6(connection):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select mems.firstname || ' ' || mems.surname as member, 
                facs.name as facility, 
                case 
                    when mems.memid = 0 then
                        bks.slots*facs.guestcost
                    else
                        bks.slots*facs.membercost
                end as cost
                    from
                            cd.members mems                
                            inner join cd.bookings bks
                                    on mems.memid = bks.memid
                            inner join cd.facilities facs
                                    on bks.facid = facs.facid
                    where
                    bks.starttime >= '2012-09-14' and 
                    bks.starttime < '2012-09-15' and (
                        (mems.memid = 0 and bks.slots*facs.guestcost > 30) or
                        (mems.memid != 0 and bks.slots*facs.membercost > 30)
                    )
            order by cost desc;      
            """
        )
        data = cursor.fetchall()
        assert len(data) == 18
        assert data[0] == ("GUEST GUEST", "Massage Room 2", 320)
        assert data[-1][2] == 35
