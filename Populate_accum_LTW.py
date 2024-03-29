import pymysql
import csv 
import time
from datetime import datetime, timedelta

connect = pymysql.connect(host='127.0.0.1', port=3306, db='ptls')
cursor = connect.cursor(pymysql.cursors.DictCursor)

 
#UPDATE accum TO THE MOST RECENT READ on dials
sql = f""" SELECT max(RealReadDate) as date FROM dials """
cursor.execute(sql)
latest_date = cursor.fetchall()[0]["date"]
if latest_date.minute < 23:
    latest_date = latest_date - timedelta(hours=1, minutes=latest_date.minute)
else:
    latest_date = latest_date - timedelta(minutes=latest_date.minute)

print(latest_date) 

sql = f""" SELECT * FROM accum WHERE RealReadDate = (SELECT MAX(RealReadDate) FROM accum) """
cursor.execute(sql)
latest_readigs = cursor.fetchall()

if len(latest_readigs) == 0:
    print("No readings in accum. Getting the first readings in dials")
    sql = f""" SELECT * FROM dials WHERE RealReadDate = (SELECT MIN(RealReadDate) FROM dials) """
    cursor.execute(sql)
    first_readigs = cursor.fetchall()

    for r in first_readigs:
        dateToInsert = r['RealReadDate'] - timedelta(minutes=r['RealReadDate'].minute)
        unixTime =  time.mktime(dateToInsert.timetuple())
        
        sql = f""" INSERT INTO accum VALUES (
                    '{r['SN']}',
                    '{unixTime}',
                    '{dateToInsert}',
                    '{0}',
                    '{0}',
                    '{0}',
                    '{0}',
                    '{0}',
                    '{0}',
                    '{0}',
                    '{0}'
                    )"""
        cursor.execute(sql)
        connect.commit()

        sql = f""" SELECT * FROM accum WHERE RealReadDate = (SELECT MAX(RealReadDate) FROM accum) """
        cursor.execute(sql)
        latest_readigs = cursor.fetchall()

date = latest_readigs[0]["RealReadDate"]

#Load multipliers
mult = {}
i = 0
for r in latest_readigs:
    mult[r["SN"]] = []
    for ch in range(1,9):
        sql = """ SELECT IFNULL(multiplier,1) as mult FROM meters where ModbusId = {} AND SN like '%0{}'
              """.format(r["SN"],ch)
        cursor.execute(sql)
        m = cursor.fetchall()
        if len(m) != 0:
            mult[r["SN"]].append(m[0]["mult"])
        else:
            mult[r["SN"]].append(1.0)

print(mult)

print("Filling accum from {} to {}".format(date, latest_date))

while date <= latest_date:
    print(date)
    for r in latest_readigs:
        try:
            #print(r)
            startDate = date + timedelta(minutes=1)
            endDate = date + timedelta(hours=1)

            sql = f""" SELECT * FROM dials WHERE SN = '{r["SN"]}' AND RealReadDate BETWEEN '{startDate}' AND '{endDate}'"""
            cursor.execute(sql)
            read = cursor.fetchall()
            #print(read)
            
            r["RealReadDate"] = endDate
            r["ReadDate"] = time.mktime(endDate.timetuple())

            for rs in read:
                r["TCh1"] = r["TCh1"] + (rs["Ch1"] * mult[r["SN"]][0])
                r["TCh2"] = r["TCh2"] + (rs["Ch2"] * mult[r["SN"]][1])
                r["TCh3"] = r["TCh3"] + (rs["Ch3"] * mult[r["SN"]][2])
                r["TCh4"] = r["TCh4"] + (rs["Ch4"] * mult[r["SN"]][3])
                r["TCh5"] = r["TCh5"] + (rs["Ch5"] * mult[r["SN"]][4])
                r["TCh6"] = r["TCh6"] + (rs["Ch6"] * mult[r["SN"]][5])
                r["TCh7"] = r["TCh7"] + (rs["Ch7"] * mult[r["SN"]][6])
                r["TCh8"] = r["TCh8"] + (rs["Ch8"] * mult[r["SN"]][7])
                #print(r)
            
            sql = f""" INSERT INTO accum VALUES (
                        '{r['SN']}',
                        '{r['ReadDate']}',
                        '{r['RealReadDate']}',
                        '{r["TCh1"]}',
                        '{r["TCh2"]}',
                        '{r["TCh3"]}',
                        '{r["TCh4"]}',
                        '{r["TCh5"]}',
                        '{r["TCh6"]}',
                        '{r["TCh7"]}',
                        '{r["TCh8"]}'
                       )
                       ON DUPLICATE KEY UPDATE
                        TCH1 = VALUES(TCH1),
                        TCH2 = VALUES(TCH2),
                        TCH3 = VALUES(TCH3),
                        TCH4 = VALUES(TCH4),
                        TCH5 = VALUES(TCH5),
                        TCH6 = VALUES(TCH6),
                        TCH7 = VALUES(TCH7),
                        TCH8 = VALUES(TCH8)
                        """
            cursor.execute(sql)
            connect.commit()
        except Exception as e:
            print(e)
    date = date + timedelta(hours=1)