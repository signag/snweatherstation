#!/usr/bin/python3
"""
Module for querying weather forecast data from OpenWeatherMap and storage in database
"""
import json
import requests
import datetime

# Set up logging
import logging
import logging_plus
logger = logging_plus.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# Defaults
# Current / hourly forecast
cfc = {
    "timestamp"   : None,
    "temperature" : None,
    "humidity"    : None,
    "pressure"    : None,
    "clouds"      : None,
    "uvi"         : None,
    "visibility"  : None,
    "windspeed"   : None,
    "winddir"     : None,
    "rain"        : None,
    "snow"        : None,
    "description" : None,
    "icon"        : None,
    "alerts"      : 0
}
# Daily forecast
dfc = {
    "date": None,
    "sunrise": None,
    "sunset": None,
    "temperature_m": None,
    "temperature_d": None,
    "temperature_e": None,
    "temperature_n": None,
    "temperature_min": None,
    "temperature_max": None,
    "humidity" : None,
    "pressure" : None,
    "windspeed" : None,
    "winddir" : None,
    "clouds" : None,
    "uvi" : None,
    "pop": None,
    "rain" : None,
    "snow" : None,
    "description" : None,
    "icon" : None,
    "alerts"      : 0
}

def getForecast(url, payload):
    """
    Get weather forecast data from openweb service
    """
    fcr = requests.get(url, params=payload)
    if fcr.status_code != requests.codes.ok:
        fcr.raise_for_status()

    return fcr.json()

def mapForecast(fc, ts):
    """
    Map forecast data to standard structure
    """
    global cfc

    # Map current forecast
    curfc = cfc.copy()
    curfc["timestamp"] = ts
    curfc["temperature"] = fc["current"]["temp"]
    curfc["humidity"] = fc["current"]["humidity"]
    curfc["pressure"] = fc["current"]["pressure"]
    curfc["clouds"] = fc["current"]["clouds"]
    curfc["uvi"] = fc["current"]["uvi"]
    curfc["visibility"] = fc["current"]["visibility"]
    curfc["windspeed"] = fc["current"]["wind_speed"]
    curfc["winddir"] = fc["current"]["wind_deg"]
    if "rain" in fc["current"]:
        curfc["rain"] = fc["current"]["rain"]["1h"]
    if "snow" in fc["current"]:
        curfc["snow"] = fc["current"]["snow"]["1h"]
    if len(fc["current"]["weather"]) > 0:
        w = fc["current"]["weather"][0]
        curfc["description"] = w["description"]
        curfc["icon"] = w["icon"]
    curfc["alerts"] = getAlerts(fc, fc["current"]["dt"])

    # Map hourly forecast
    hourlyfc = list()
    if len(fc["hourly"]) > 0:
        for i in range(0, len(fc["hourly"])):
            hourfc = cfc.copy()
            hfc = fc["hourly"][i]
            hourfc["timestamp"] = datetime.datetime.fromtimestamp(hfc["dt"]).strftime("%Y-%m-%d %H:%M:%S")
            hourfc["temperature"] = hfc["temp"]
            hourfc["humidity"] = hfc["humidity"]
            hourfc["pressure"] = hfc["pressure"]
            hourfc["clouds"] = hfc["clouds"]
            hourfc["uvi"] = hfc["uvi"]
            hourfc["visibility"] = hfc["visibility"]
            hourfc["windspeed"] = hfc["wind_speed"]
            hourfc["winddir"] = hfc["wind_deg"]
            if "rain" in hfc:
                hourfc["rain"] = hfc["rain"]["1h"]
            if "snow" in hfc:
                hourfc["snow"] = hfc["snow"]["1h"]
            if len(hfc["weather"]) > 0:
                w = hfc["weather"][0]
                hourfc["description"] = w["description"]
                hourfc["icon"] = w["icon"]
                hourfc["alerts"] = getAlerts(fc, hfc["dt"])

            hourlyfc.append(hourfc)
    
    # Map daily forecast
    dailyfc = list()
    if len(fc["daily"]) > 0:
        for i in range(0, len(fc["daily"])):
            dayfc = dfc.copy()
            dyfc = fc["daily"][i]
            dayfc["date"] = datetime.datetime.fromtimestamp(dyfc["dt"]).strftime("%Y-%m-%d")
            dayfc["sunrise"] = datetime.datetime.fromtimestamp(dyfc["sunrise"]).strftime("%H:%M:%S")
            dayfc["sunset"] = datetime.datetime.fromtimestamp(dyfc["sunset"]).strftime("%H:%M:%S")
            dyfct = dyfc["temp"]
            dayfc["temperature_m"] = dyfct["morn"]
            dayfc["temperature_d"] = dyfct["day"]
            dayfc["temperature_e"] = dyfct["eve"]
            dayfc["temperature_n"] = dyfct["night"]
            dayfc["temperature_min"] = dyfct["min"]
            dayfc["temperature_max"] = dyfct["max"]
            dayfc["humidity"] = dyfc["humidity"]
            dayfc["pressure"] = dyfc["pressure"]
            dayfc["windspeed"] = dyfc["wind_speed"]
            dayfc["winddir"] = dyfc["wind_deg"]
            dayfc["clouds"] = dyfc["clouds"]
            dayfc["uvi"] = dyfc["uvi"]
            dayfc["pop"] = dyfc["pop"]
            if "rain" in dyfc:
                dayfc["rain"] = dyfc["rain"]
            if "snow" in dyfc:
                dayfc["snow"] = dyfc["snow"]
            if len(dyfc["weather"]) > 0:
                w = dyfc["weather"][0]
                dayfc["description"] = w["description"]
                dayfc["icon"] = w["icon"]
                dayfc["alerts"] = getAlerts(fc, dyfc["dt"])

            dailyfc.append(dayfc)

    return [curfc, hourlyfc, dailyfc]

def getAlerts(fc, dt):
    """
    Count the number of alerts for a given date/time (dt)
    """
    res = 0

    if "alerts" in fc:
        if len(fc["alerts"]) > 0:
            for i in range(0, len(fc["alerts"])):
                alert = fc["alerts"][i]
                if dt >= alert["start"] and dt <= alert["end"]:
                    res = res + 1
    return res

def forecastToDb(fcData, cfg, curTs, curDate, dbCon, dbCur, servRun):
    """
    Store forecast data in database
    """

    #
    # Store current and hourly forecast
    #
    tblHourly     = cfg["forecast"]["forecastTables"]["hourlyForecast"]

    # Clean up current / hourly forecast
    # Retain forecast for the next fcRetainHours hours
    fcRetainHours = cfg["forecast"]["forecastRetain"]

    t_lastTs = getLatestForecast(tblHourly, dbCon, dbCur, servRun)
    if t_lastTs:
        t_lastTs = t_lastTs + datetime.timedelta(minutes=1)
        t_curTs  = datetime.datetime.strptime(curTs, "%Y-%m-%d %H:%M:%S")
        t_limTs  = t_curTs + datetime.timedelta(hours=fcRetainHours)
        if t_lastTs < t_limTs:
            t_limTs = t_lastTs
        limTs    = t_limTs.strftime("%Y-%m-%d %H:%M:%S")
    else:
        limTs = curTs
    forecastToDbHourlyCleanup(tblHourly, limTs, dbCon, dbCur, servRun)

    # Insert Current forecast
    curfc = fcData[0]
    forecastToDbCurrent(curfc, tblHourly, dbCon, dbCur, servRun)

    # Insert hourly forecast
    hourfc = fcData[1]
    if len(hourfc) > 0:
        for i in range(0, len(hourfc)):
            curfc = hourfc[i]
            if curfc["timestamp"] > limTs:
                forecastToDbHourly(curfc, tblHourly, dbCon, dbCur, servRun)
    #
    # Store daily forecast
    #
    tblDaily = cfg["forecast"]["forecastTables"]["dailyForecast"]

    # Clean up daily forecast
    forecastToDbDailyCleanup(tblDaily, curDate, dbCon, dbCur, servRun)

    # Insert daily forecast
    dayfc = fcData[2]
    if len(dayfc) > 0:
        for i in range(0, len(dayfc)):
            curfc = dayfc[i]
            if curfc["date"] >= curDate:
                forecastToDbDaily(curfc, tblDaily, dbCon, dbCur, servRun)

def getLatestForecast(tbl, dbCon, dbCur, servRun):
    """
    Return the timestamp for the latest forecast.
    """
    # Prepare statement
    stmt = "SELECT timestamp FROM " + tbl + " ORDER BY TIMESTAMP DESC LIMIT 0,1"
 
    logger.debug(stmt)
    dbCur.execute(stmt)

    res = None
    for (timestamp) in dbCur:
        res = timestamp[0]

    return res

def forecastToDbHourlyCleanup(tbl, ts, dbCon, dbCur, servRun):
    """
    Remove entries for later timestamps.

    This is necessary in order to allow later insertion of forecast entries
    """
    # Prepare statement
    stmt = "DELETE FROM " + tbl + " WHERE timestamp >= '" + ts + "'"

    logger.debug(stmt)
    dbCur.execute(stmt)
    dbCon.commit()

def forecastToDbDailyCleanup(tbl, curDate, dbCon, dbCur, servRun):
    """
    Remove entries for later timestamps.

    This is necessary in order to allow later insertion of forecast entries
    """
    
    # Prepare statement
    stmt = "DELETE FROM " + tbl + " WHERE date >= '" + curDate + "'"

    logger.debug(stmt)
    dbCur.execute(stmt)
    dbCon.commit()

def forecastToDbCurrent(fc, tbl, dbCon, dbCur, servRun):
    """
    Store current forecast data in database
    """
    global logger

    # Prepare statement
    ins1 = "INSERT INTO " + tbl + " (timestamp"
    ins2 = "VALUES ('"  + fc["timestamp"] + "'"
    ins3 = " ON DUPLICATE KEY UPDATE "

    if fc["temperature"] != None:
        ins1 = ins1 + ", temperature"
        ins2 = ins2 + ", " + "{:+.1f}".format(fc["temperature"])
        ins3 = ins3 + "temperature="
        ins3 = ins3 + "{:+.1f}".format(fc["temperature"])
    if fc["humidity"] != None:
        ins1 = ins1 + ", humidity"
        ins2 = ins2 + ", " + "{:+.1f}".format(fc["humidity"])
        ins3 = ins3 + ", humidity="
        ins3 = ins3 + "{:+.1f}".format(fc["humidity"])
    if fc["pressure"] != None:
        ins1 = ins1 + ", pressure"
        ins2 = ins2 + ", " + "{:+.1f}".format(fc["pressure"])
        ins3 = ins3 + ", pressure="
        ins3 = ins3 + "{:+.1f}".format(fc["pressure"])
    if fc["clouds"] != None:
        ins1 = ins1 + ", clouds"
        ins2 = ins2 + ", " + "{:+.1f}".format(fc["clouds"])
        ins3 = ins3 + ", clouds="
        ins3 = ins3 + "{:+.1f}".format(fc["clouds"])
    if fc["uvi"] != None:
        ins1 = ins1 + ", uvi"
        ins2 = ins2 + ", " + "{:+.2f}".format(fc["uvi"])
        ins3 = ins3 + ", uvi="
        ins3 = ins3 + "{:+.2f}".format(fc["uvi"])
    if fc["visibility"] != None:
        ins1 = ins1 + ", visibility"
        ins2 = ins2 + ", " + "{:+.1f}".format(fc["visibility"])
        ins3 = ins3 + ", visibility="
        ins3 = ins3 + "{:+.1f}".format(fc["visibility"])
    if fc["windspeed"] != None:
        ins1 = ins1 + ", windspeed"
        ins2 = ins2 + ", " + "{:+.1f}".format(fc["windspeed"])
        ins3 = ins3 + ", windspeed="
        ins3 = ins3 + "{:+.1f}".format(fc["windspeed"])
    if fc["winddir"] != None:
        ins1 = ins1 + ", winddir"
        ins2 = ins2 + ", " + "{:+.1f}".format(fc["winddir"])
        ins3 = ins3 + ", winddir="
        ins3 = ins3 + "{:+.1f}".format(fc["winddir"])
    if fc["rain"] != None:
        ins1 = ins1 + ", rain"
        ins2 = ins2 + ", " + "{:+.2f}".format(fc["rain"])
        ins3 = ins3 + ", rain="
        ins3 = ins3 + "{:+.2f}".format(fc["rain"])
    if fc["snow"] != None:
        ins1 = ins1 + ", snow"
        ins2 = ins2 + ", " + "{:+.2f}".format(fc["snow"])
        ins3 = ins3 + ", snow="
        ins3 = ins3 + "{:+.2f}".format(fc["snow"])
    if fc["description"] != None:
        ins1 = ins1 + ", description"
        ins2 = ins2 + ", '" + fc["description"] + "'"
        ins3 = ins3 + ", description="
        ins3 = ins3 + "'" + fc["description"] + "'"
    if fc["icon"] != None:
        ins1 = ins1 + ", icon"
        ins2 = ins2 + ", '" + fc["icon"] + "'"
        ins3 = ins3 + ", icon="
        ins3 = ins3 + "'" + fc["icon"] + "'"
    if fc["alerts"] != None:
        ins1 = ins1 + ", alerts"
        ins2 = ins2 + ", " + "{}".format(fc["alerts"])
        ins3 = ins3 + ", alerts="
        ins3 = ins3 + "{}".format(fc["alerts"])

    tnow = datetime.datetime.now()
    ins1 = ins1 + ", time_cre"
    ins2 = ins2 + ", '" + tnow.strftime("%Y-%m-%d %H:%M:%S") + "'"
    ins1 = ins1 + ", time_mod"
    ins2 = ins2 + ", '" + tnow.strftime("%Y-%m-%d %H:%M:%S") + "'"
    ins3 = ins3 + ", time_mod="
    ins3 = ins3 + "'" + tnow.strftime("%Y-%m-%d %H:%M:%S") + "'"

    # Insert Current forecast
    ins = ins1 + ") " + ins2 + ")" + ins3
    logger.debug(ins)
    dbCur.execute(ins)
    dbCon.commit()

def forecastToDbHourly(fc, tbl, dbCon, dbCur, servRun):
    """
    Store forecast data in database
    """
    # Prepare statement
    ins1 = "INSERT INTO " + tbl + " (timestamp"
    ins2 = "VALUES ('"  + fc["timestamp"] + "'"

    if fc["temperature"] != None:
        ins1 = ins1 + ", temperature"
        ins2 = ins2 + ", " + "{:+.1f}".format(fc["temperature"])
        ins1 = ins1 + ", temperature_fc"
        ins2 = ins2 + ", " + "{:+.1f}".format(fc["temperature"])
    if fc["humidity"] != None:
        ins1 = ins1 + ", humidity"
        ins2 = ins2 + ", " + "{:+.1f}".format(fc["humidity"])
        ins1 = ins1 + ", humidity_fc"
        ins2 = ins2 + ", " + "{:+.1f}".format(fc["humidity"])
    if fc["pressure"] != None:
        ins1 = ins1 + ", pressure"
        ins2 = ins2 + ", " + "{:+.1f}".format(fc["pressure"])
        ins1 = ins1 + ", pressure_fc"
        ins2 = ins2 + ", " + "{:+.1f}".format(fc["pressure"])
    if fc["clouds"] != None:
        ins1 = ins1 + ", clouds"
        ins2 = ins2 + ", " + "{:+.1f}".format(fc["clouds"])
    if fc["uvi"] != None:
        ins1 = ins1 + ", uvi"
        ins2 = ins2 + ", " + "{:+.2f}".format(fc["uvi"])
    if fc["visibility"] != None:
        ins1 = ins1 + ", visibility"
        ins2 = ins2 + ", " + "{:+.1f}".format(fc["visibility"])
    if fc["windspeed"] != None:
        ins1 = ins1 + ", windspeed"
        ins2 = ins2 + ", " + "{:+.1f}".format(fc["windspeed"])
    if fc["winddir"] != None:
        ins1 = ins1 + ", winddir"
        ins2 = ins2 + ", " + "{:+.1f}".format(fc["winddir"])
    if fc["rain"] != None:
        ins1 = ins1 + ", rain"
        ins2 = ins2 + ", " + "{:+.2f}".format(fc["rain"])
    if fc["snow"] != None:
        ins1 = ins1 + ", snow"
        ins2 = ins2 + ", " + "{:+.2f}".format(fc["snow"])
    if fc["description"] != None:
        ins1 = ins1 + ", description"
        ins2 = ins2 + ", '" + fc["description"] + "'"
    if fc["icon"] != None:
        ins1 = ins1 + ", icon"
        ins2 = ins2 + ", '" + fc["icon"] + "'"
    if fc["alerts"] != None:
        ins1 = ins1 + ", alerts"
        ins2 = ins2 + ", " + "{}".format(fc["alerts"])


    tnow = datetime.datetime.now()
    ins1 = ins1 + ", time_cre"
    ins2 = ins2 + ", '" + tnow.strftime("%Y-%m-%d %H:%M:%S") + "'"
    ins1 = ins1 + ", time_mod"
    ins2 = ins2 + ", '" + tnow.strftime("%Y-%m-%d %H:%M:%S") + "'"

    # Insert Current forecast
    ins = ins1 + ") " + ins2 + ")"
    logger.debug(ins)
    dbCur.execute(ins)
    dbCon.commit()

def forecastToDbDaily(fc, tbl, dbCon, dbCur, servRun):
    """
    Store forecast data in database
    """
    # Prepare statement
    ins1 = "INSERT INTO " + tbl + " (date"
    ins2 = "VALUES ('"  + fc["date"] + "'"

    if fc["sunrise"] != None:
        ins1 = ins1 + ", sunrise"
        ins2 = ins2 + ", '" + fc["sunrise"] + "'"
    if fc["sunset"] != None:
        ins1 = ins1 + ", sunset"
        ins2 = ins2 + ", '" + fc["sunset"] + "'"
    if fc["temperature_m"] != None:
        ins1 = ins1 + ", temperature_m"
        ins2 = ins2 + ", " + "{:+.1f}".format(fc["temperature_m"])
    if fc["temperature_d"] != None:
        ins1 = ins1 + ", temperature_d"
        ins2 = ins2 + ", " + "{:+.1f}".format(fc["temperature_d"])
    if fc["temperature_e"] != None:
        ins1 = ins1 + ", temperature_e"
        ins2 = ins2 + ", " + "{:+.1f}".format(fc["temperature_e"])
    if fc["temperature_n"] != None:
        ins1 = ins1 + ", temperature_n"
        ins2 = ins2 + ", " + "{:+.1f}".format(fc["temperature_n"])
    if fc["temperature_min"] != None:
        ins1 = ins1 + ", temperature_min"
        ins2 = ins2 + ", " + "{:+.1f}".format(fc["temperature_min"])
    if fc["temperature_max"] != None:
        ins1 = ins1 + ", temperature_max"
        ins2 = ins2 + ", " + "{:+.1f}".format(fc["temperature_max"])
    if fc["humidity"] != None:
        ins1 = ins1 + ", humidity"
        ins2 = ins2 + ", " + "{:+.1f}".format(fc["humidity"])
    if fc["pressure"] != None:
        ins1 = ins1 + ", pressure"
        ins2 = ins2 + ", " + "{:+.1f}".format(fc["pressure"])
    if fc["windspeed"] != None:
        ins1 = ins1 + ", windspeed"
        ins2 = ins2 + ", " + "{:+.1f}".format(fc["windspeed"])
    if fc["winddir"] != None:
        ins1 = ins1 + ", winddir"
        ins2 = ins2 + ", " + "{:+.1f}".format(fc["winddir"])
    if fc["clouds"] != None:
        ins1 = ins1 + ", clouds"
        ins2 = ins2 + ", " + "{:+.1f}".format(fc["clouds"])
    if fc["uvi"] != None:
        ins1 = ins1 + ", uvi"
        ins2 = ins2 + ", " + "{:+.2f}".format(fc["uvi"])
    if fc["pop"] != None:
        ins1 = ins1 + ", pop"
        ins2 = ins2 + ", " + "{:+.2f}".format(fc["pop"])
    if fc["rain"] != None:
        ins1 = ins1 + ", rain"
        ins2 = ins2 + ", " + "{:+.2f}".format(fc["rain"])
    if fc["snow"] != None:
        ins1 = ins1 + ", snow"
        ins2 = ins2 + ", " + "{:+.2f}".format(fc["snow"])
    if fc["description"] != None:
        ins1 = ins1 + ", description"
        ins2 = ins2 + ", '" + fc["description"] + "'"
    if fc["icon"] != None:
        ins1 = ins1 + ", icon"
        ins2 = ins2 + ", '" + fc["icon"] + "'"
    if fc["alerts"] != None:
        ins1 = ins1 + ", alerts"
        ins2 = ins2 + ", " + "{}".format(fc["alerts"])

    # Insert Current forecast
    ins = ins1 + ") " + ins2 + ")"
    logger.debug(ins)
    dbCur.execute(ins)
    dbCon.commit()

def alertsToDb(fc, cfg, dbCon, dbCur, servRun):
    """
    Store alerts in database
    """

    tbl = cfg["forecast"]["forecastTables"]["alertsForecast"]

    if "alerts" in fc:
        if len(fc["alerts"]) > 0:
            for i in range(0, len(fc["alerts"])):
                alert = fc["alerts"][i]
                # Prepare statement
                ins1 = "INSERT INTO " + tbl + " ("
                ins2 = "VALUES ("
                ins3 = " ON DUPLICATE KEY UPDATE "
                
                ins1 = ins1 + "start"
                ins2 = ins2 + "'" + datetime.datetime.fromtimestamp(alert["start"]).strftime("%Y-%m-%d %H:%M:%S") + "'"

                ins1 = ins1 + ", end"
                ins2 = ins2 + ", '" + datetime.datetime.fromtimestamp(alert["end"]).strftime("%Y-%m-%d %H:%M:%S") + "'"

                ins1 = ins1 + ", event"
                ins2 = ins2 + ", '" + alert["event"] + "'"

                ins1 = ins1 + ", sender_name"
                ins2 = ins2 + ", '" + alert["sender_name"] + "'"

                ins1 = ins1 + ", description"
                ins2 = ins2 + ", '" + alert["description"] + "'"
                ins3 = ins3 + "description='" + alert["description"] + "'"

                # Insert Current forecast
                ins = ins1 + ") " + ins2 + ")" + ins3
                logger.debug(ins)
                dbCur.execute(ins)
                dbCon.commit()


def forecastToFile(fc, cfg, curTs, fil, servRun):
    """
    Store forecast data in database
    """
    fil.write('{')
    fil.write('"time": "' + curTs + '",')
    fil.write('"data":')
    fil.write(json.dumps(fc))
    fil.write('}')

def handleForecast(cfg, curTs, curDate, curTime, dbCon, dbCur, fil, servRun):
    """
    Handle forecast according to given configuration

    Input:
    - cfg    : Configuration dictionary for weatherstation
    - curTS  : Measurement timestamp
    - curDate: Measurement Date
    - curTime: Measurement Time
    - dbCon  : Database connection
    - dbCur  : Database cursor
    - fil    : file handler for outpot file
    - servRun: True for service run
    """
    # Get the forecast
    url = cfg["forecast"]["source"]["url"]
    payload = cfg["forecast"]["source"]["payload"]
    fc = getForecast(url, payload)

    # Output to file
    if cfg["forecast"]["forecastFileOut"]:
        forecastToFile(fc, cfg, curTs, fil, servRun)

    # Map forecast
    fcData = mapForecast(fc, curTs)

    # Store in database
    if cfg["forecast"]["forecastDbOut"]:
        forecastToDb(fcData, cfg, curTs, curDate, dbCon, dbCur, servRun)

    # Store alerts
    if cfg["forecast"]["forecastDbOut"]:
        alertsToDb(fc, cfg, dbCon, dbCur, servRun)