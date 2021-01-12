#!/usr/bin/python3
"""
Module weatherStation

This module includes functions for a weather station
"""

from snraspi.sensors import EnvironmentSensor
import time
import datetime
import mariadb
import sys
import math
import os.path
import json
import weatherForecastOWM

# Set up logging
import logging
from logging.config import dictConfig
import logging_plus
logger = logging_plus.getLogger("main")

testRun = False
servRun = False

# Configuration defaults
cfgFile = ""
cfg = {
    "sensorType"         : "BME280_I2C",
    "raspiPin"           : None,
    "raspiPinObj"        : None,
    "measurementInterval": 2,
    "height"             : None,
    "dbOut"              : False,
    "fileOut"            : False,
    "includeForecast"    : False,
    "dbConnection":
    {
        "host"    : None, 
        "port"    : None, 
        "database": None, 
        "table"   : None,
        "user"    : None, 
        "password": None
    },
    "fileName": None,
    "forecast":
    {
        "source":
        {
            "url": "https://api.openweathermap.org/data/2.5/onecall",
            "payload":
            {
                "lat"   : None,
                "lon"   : None,
                "units" : "metric",
                "lang"  : "de",
                "appid" : None
            }
        },
        "forecastDbOut  ": False,
        "forecastFileOut": False,
        "forecastRetain" : 4,
        "forecastTables" :
        {
            "hourlyForecast": None,
            "dailyForecast" : None,
            "alertsForecast": None
        },
        "forecastFile": None
    }
}

# Constants
CFGFILENAME = "weatherstation.json"

def getCl():
    """
    getCL: Get and process command line parameters
    """

    import argparse
    import os.path

    global logger
    global testRun
    global servRun
    global cfgFile

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=
    """
    This program periodically reads environment sensor data
    and stores these either in the database and/or in a file and/or just prints measured values.

    If not otherwises specified on the command line, a configuration file
       weatherstation.json
    will be searched sequentially under ./tests/data, $HOME/.config or /etc.

    This configuration file specifies the database connection and other runtime parameters.
    """
    )
    parser.add_argument("-t", "--test", action = "store_true", help="Test run - single cycle - no wait")
    parser.add_argument("-s", "--service", action = "store_true", help="Run as service - special logging")
    parser.add_argument("-l", "--log", action = "store_true", help="Shallow (module) logging")
    parser.add_argument("-L", "--Log", action = "store_true", help="Deep logging")
    parser.add_argument("-F", "--Full", action = "store_true", help="Full logging")
    parser.add_argument("-f", "--file", help="Logging configuration from specified JSON dictionary file")
    parser.add_argument("-v", "--verbose", action = "store_true", help="Verbose - log INFO level")
    parser.add_argument("-c", "--config", help="Path to config file to be used")

    args = parser.parse_args()

    # Disable logging
    logger = logging_plus.getLogger("main")
    logger.addHandler(logging.NullHandler())
    rLogger = logging_plus.getLogger()
    rLogger.addHandler(logging.NullHandler())
    eLogger = logging_plus.getLogger(EnvironmentSensor.__name__)
    eLogger.addHandler(logging.NullHandler())
    fLogger = logging_plus.getLogger(weatherForecastOWM.__name__)
    fLogger.addHandler(logging.NullHandler())

    # Set handler and formatter to be used
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
    formatter2 = logging.Formatter('%(asctime)s %(name)-33s %(levelname)-8s %(message)s')
    handler.setFormatter(formatter)

    if args.log:
        # Shallow logging
        handler.setFormatter(formatter2)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        eLogger.addHandler(handler)
        eLogger.setLevel(logging.DEBUG)
        fLogger.addHandler(handler)
        fLogger.setLevel(logging.DEBUG)

    if args.Log:
        # Deep logging
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        eLogger.addHandler(handler)
        eLogger.setLevel(logging.DEBUG)
        fLogger.addHandler(handler)
        fLogger.setLevel(logging.DEBUG)
        # Activate logging of function entry and exit
        logging_plus.registerAutoLogEntryExit()

    if args.Full:
        # Full logging
        rLogger.addHandler(handler)
        rLogger.setLevel(logging.DEBUG)
        # Activate logging of function entry and exit
        logging_plus.registerAutoLogEntryExit()

    if args.file:
        # Logging configuration from file
        logDictFile = args.file
        if not os.path.exists(logDictFile):
            raise ValueError("Logging dictionary file from command line does not exist: " + logDictFile)

        # Load dictionary
        with open(logDictFile, 'r') as f:
            logDict = json.load(f)

        # Set config file for logging
        dictConfig(logDict)
        logger = logging.getLogger()
        EnvironmentSensor.logger = logging.getLogger(EnvironmentSensor.__name__)
        # Activate logging of function entry and exit
        #logging_plus.registerAutoLogEntryExit()

    # Explicitly log entry
    if args.Log or args.Full:
        logger.logEntry("getCL")
    if args.log:
        logger.debug("Shallow logging (main only)")
    if args.Log:
        logger.debug("Deep logging")
    if args.file:
        logger.debug("Logging dictionary from %s", logDictFile)

    if args.verbose or args.service:
        if not args.log and not args.Log and not args.Full:
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)

    if args.test:
        testRun = True

    if args.service:
        servRun = True

    if testRun:    
        logger.debug("Test run mode activated")
    else:
        logger.debug("Test run mode deactivated")
        
    if servRun:    
        logger.debug("Service run mode activated")
    else:
        logger.debug("Service run mode deactivated")

    if args.config:
        cfgFile = args.config
        logger.debug("Config file: %s", cfgFile)
    else:
        logger.debug("No Config file specified on command line")

    if args.Log or args.Full:
        logger.logExit("getCL")

def getConfig():
    """
    Get configuration for weatherstation
    """
    global cfgFile
    global cfg
    global logger

    # Check config file from command line
    if cfgFile != "":
        if not os.path.exists(cfgFile):
            raise ValueError("Configuration file from command line does not exist: ", cfgFile)
        logger.info("Using cfgFile from command line: %s", cfgFile)

    if cfgFile == "":
        # Check for config file in ./tests/data directory
        curDir = os.path.dirname(os.path.realpath(__file__))
        curDir = os.path.dirname(curDir)
        cfgFile = curDir + "/tests/data/" + CFGFILENAME
        if not os.path.exists(cfgFile):
            # Check for config file in /etc directory
            logger.info("Config file not found: %s", cfgFile)
            cfgFile = ""

    if cfgFile == "":
        # Check for config file in home directory
        homeDir = os.environ['HOME']
        cfgFile = homeDir + "/.config/" + CFGFILENAME
        if not os.path.exists(cfgFile):
            # Check for config file in /etc directory
            logger.info("Config file not found: %s", cfgFile)
            cfgFile = "/etc/" + CFGFILENAME
            if not os.path.exists(cfgFile):
                logger.info("Config file not found: %s", cfgFile)
                cfgFile = ""

    if cfgFile == "":
        # No cfg available 
        logger.info("No config file available. Using default configuration")
    else:
        logger.info("Using cfgFile: %s", cfgFile)
        with open(cfgFile, 'r') as f:
            conf = json.load(f)
            if "sensorType" in conf:
                if conf["sensorType"] not in EnvironmentSensor.sensorTypes:
                    raise ValueError("Invalid sensorType specified in Configuration file. Allowed types are:", EnvironmentSensor.sensorTypes)
                cfg["sensorType"] = conf["sensorType"]
            if "raspiPin" in conf:
                cfg["raspiPin"] = conf["raspiPin"]
            else:
                if cfg["sensorType"] == EnvironmentSensor.type_BME280_SPI \
                or cfg["sensorType"] == EnvironmentSensor.type_DHT11 \
                or cfg["sensorType"] == EnvironmentSensor.type_DHT22:
                    raise ValueError("Configuration file requires raspiPin for sensor type ", cfg["sensorType"])
            if "measurementInterval" in conf:
                cfg["measurementInterval"] = conf["measurementInterval"]
            if "height" in conf:
                cfg["height"] = conf["height"]
            else:
                raise ValueError("Configuration file requires height")
            if "dbOut" in conf:
                cfg["dbOut"] = conf["dbOut"]
            if "fileOut" in conf:
                cfg["fileOut"] = conf["fileOut"]
            if "includeForecast" in conf:
                cfg["includeForecast"] = conf["includeForecast"]
            if cfg["dbOut"]:
                if "dbConnection" in conf:
                    if "host" in conf["dbConnection"]:
                        cfg["dbConnection"]["host"] = conf["dbConnection"]["host"]
                    else:
                        raise ValueError("Configuration file requires dbConnection.host")
                    if "port" in conf["dbConnection"]:
                        cfg["dbConnection"]["port"] = conf["dbConnection"]["port"]
                    else:
                        raise ValueError("Configuration file requires dbConnection.port")
                    if "database" in conf["dbConnection"]:
                        cfg["dbConnection"]["database"] = conf["dbConnection"]["database"]
                    else:
                        raise ValueError("Configuration file requires dbConnection.database")
                    if "table" in conf["dbConnection"]:
                        cfg["dbConnection"]["table"] = conf["dbConnection"]["table"]
                    else:
                        raise ValueError("Configuration file requires dbConnection.table")
                    if "user" in conf["dbConnection"]:
                        cfg["dbConnection"]["user"] = conf["dbConnection"]["user"]
                    else:
                        raise ValueError("Configuration file requires dbConnection.user")
                    if "password" in conf["dbConnection"]:
                        cfg["dbConnection"]["password"] = conf["dbConnection"]["password"]
                    else:
                        raise ValueError("Configuration file requires dbConnection.password")
                else:
                    raise ValueError("Configuration file requires dbConnection")
            if cfg["fileOut"]:
                if "fileName" in conf:
                    cfg["fileName"] = conf["fileName"]
                else:
                    raise ValueError("Configuration file requires fileName")
            if cfg["includeForecast"]:
                if "forecast" in conf:
                    if "source" in conf["forecast"]:
                        if "url" in conf["forecast"]["source"]:
                            cfg["forecast"]["source"]["url"] = conf["forecast"]["source"]["url"]
                        if "payload" in conf["forecast"]["source"]:
                            if "lat" in conf["forecast"]["source"]["payload"]:
                                cfg["forecast"]["source"]["payload"]["lat"] = conf["forecast"]["source"]["payload"]["lat"]
                            else:
                                raise ValueError("Configuration file requires forecast.source.payload.lat")
                            if "lon" in conf["forecast"]["source"]["payload"]:
                                cfg["forecast"]["source"]["payload"]["lon"] = conf["forecast"]["source"]["payload"]["lon"]
                            else:
                                raise ValueError("Configuration file requires forecast.source.payload.lon")
                            if "units" in conf["forecast"]["source"]["payload"]:
                                cfg["forecast"]["source"]["payload"]["units"] = conf["forecast"]["source"]["payload"]["units"]
                            if "lang" in conf["forecast"]["source"]["payload"]:
                                cfg["forecast"]["source"]["payload"]["lang"] = conf["forecast"]["source"]["payload"]["lang"]
                            if "appid" in conf["forecast"]["source"]["payload"]:
                                cfg["forecast"]["source"]["payload"]["appid"] = conf["forecast"]["source"]["payload"]["appid"]
                            else:
                                raise ValueError("Configuration file requires forecast.source.payload.appid")
                        else:
                            raise ValueError("Configuration file requires forecast.source.payload")
                    else:
                        raise ValueError("Configuration file requires forecast.source")
                    if "forecastDbOut" in conf["forecast"]:
                        cfg["forecast"]["forecastDbOut"] = conf["forecast"]["forecastDbOut"]
                    if cfg["forecast"]["forecastDbOut"]:
                        if not cfg["dbOut"]:
                            raise ValueError("Configuration file requires dbConnection for forecastDbOut")
                    if "forecastFileOut" in conf["forecast"]:
                        cfg["forecast"]["forecastFileOut"] = conf["forecast"]["forecastFileOut"]
                    if "forecastRetain" in conf["forecast"]:
                        cfg["forecast"]["forecastRetain"] = conf["forecast"]["forecastRetain"]
                    if cfg["forecast"]["forecastDbOut"]:
                        if "forecastTables" in conf["forecast"]:
                            if "hourlyForecast" in conf["forecast"]["forecastTables"]:
                                cfg["forecast"]["forecastTables"]["hourlyForecast"] = conf["forecast"]["forecastTables"]["hourlyForecast"]
                            else:
                                raise ValueError("Configuration file requires forecast.forecastTables.hourlyForecast")
                            if "dailyForecast" in conf["forecast"]["forecastTables"]:
                                cfg["forecast"]["forecastTables"]["dailyForecast"] = conf["forecast"]["forecastTables"]["dailyForecast"]
                            else:
                                raise ValueError("Configuration file requires forecast.forecastTables.dailyForecast")
                            if "alertsForecast" in conf["forecast"]["forecastTables"]:
                                cfg["forecast"]["forecastTables"]["alertsForecast"] = conf["forecast"]["forecastTables"]["alertsForecast"]
                            else:
                                raise ValueError("Configuration file requires forecast.forecastTables.alertsForecast")
                        else:
                            raise ValueError("Configuration file requires forecast.forecastTables")
                    if cfg["forecast"]["forecastFileOut"]:
                        if "forecastFile" in conf["forecast"]:
                            cfg["forecast"]["forecastFile"] = conf["forecast"]["forecastFile"]
                        else:
                            raise ValueError("Configuration file requires forecast.forecastFile")
                else:
                    raise ValueError("Configuration file requires forecast")

    # Check raspiPin
    pin = cfg["raspiPin"]
    if pin == "":
        if cfg["sensorType"] == EnvironmentSensor.type_BME280_SPI \
        or cfg["sensorType"] == EnvironmentSensor.type_DHT11 \
        or cfg["sensorType"] == EnvironmentSensor.type_DHT22:
            raise ValueError("Configuration file requires raspiPin for sensor type ", cfg["sensorType"])
    elif pin == "PIN03":
        cfg["raspiPinObj"] = EnvironmentSensor.PIN03
    elif pin == "PIN05":
        cfg["raspiPinObj"] = EnvironmentSensor.PIN05
    elif pin == "PIN07":
        cfg["raspiPinObj"] = EnvironmentSensor.PIN07
    elif pin == "PIN08":
        cfg["raspiPinObj"] = EnvironmentSensor.PIN08
    elif pin == "PIN10":
        cfg["raspiPinObj"] = EnvironmentSensor.PIN10
    elif pin == "PIN11":
        cfg["raspiPinObj"] = EnvironmentSensor.PIN11
    elif pin == "PIN12":
        cfg["raspiPinObj"] = EnvironmentSensor.PIN12
    elif pin == "PIN13":
        cfg["raspiPinObj"] = EnvironmentSensor.PIN13
    elif pin == "PIN15":
        cfg["raspiPinObj"] = EnvironmentSensor.PIN15
    elif pin == "PIN16":
        cfg["raspiPinObj"] = EnvironmentSensor.PIN16
    elif pin == "PIN18":
        cfg["raspiPinObj"] = EnvironmentSensor.PIN18
    elif pin == "PIN19":
        cfg["raspiPinObj"] = EnvironmentSensor.PIN19
    elif pin == "PIN21":
        cfg["raspiPinObj"] = EnvironmentSensor.PIN21
    elif pin == "PIN22":
        cfg["raspiPinObj"] = EnvironmentSensor.PIN22
    elif pin == "PIN23":
        cfg["raspiPinObj"] = EnvironmentSensor.PIN23
    elif pin == "PIN24":
        cfg["raspiPinObj"] = EnvironmentSensor.PIN24
    elif pin == "PIN26":
        cfg["raspiPinObj"] = EnvironmentSensor.PIN26
    elif pin == "PIN27":
        cfg["raspiPinObj"] = EnvironmentSensor.PIN27
    elif pin == "PIN28":
        cfg["raspiPinObj"] = EnvironmentSensor.PIN28
    elif pin == "PIN29":
        cfg["raspiPinObj"] = EnvironmentSensor.PIN29
    elif pin == "PIN31":
        cfg["raspiPinObj"] = EnvironmentSensor.PIN31
    elif pin == "PIN32":
        cfg["raspiPinObj"] = EnvironmentSensor.PIN32
    elif pin == "PIN33":
        cfg["raspiPinObj"] = EnvironmentSensor.PIN33
    elif pin == "PIN35":
        cfg["raspiPinObj"] = EnvironmentSensor.PIN35
    elif pin == "PIN36":
        cfg["raspiPinObj"] = EnvironmentSensor.PIN36
    elif pin == "PIN37":
        cfg["raspiPinObj"] = EnvironmentSensor.PIN37
    elif pin == "PIN38":
        cfg["raspiPinObj"] = EnvironmentSensor.PIN38
    elif pin == "PIN40":
        cfg["raspiPinObj"] = EnvironmentSensor.PIN40
    else:
        raise ValueError("Invalid raspiPin in configuration file: ", pin)

    logger.info("Configuration:")
    logger.info("    sensorType:         %s", cfg["sensorType"])
    logger.info("    raspiPin:           %s", cfg["raspiPin"])
    logger.info("    measurementInterval:%s", cfg["measurementInterval"])
    logger.info("    height:             %s", cfg["height"])
    logger.info("    dbOut:              %s", cfg["dbOut"])
    logger.info("       host:            %s", cfg["dbConnection"]["host"])
    logger.info("       port:            %s", cfg["dbConnection"]["port"])
    logger.info("       database:        %s", cfg["dbConnection"]["database"])
    logger.info("       table:           %s", cfg["dbConnection"]["table"])
    logger.info("       user:            %s", cfg["dbConnection"]["user"])
    logger.info("       password:        %s", cfg["dbConnection"]["password"])
    logger.info("    fileOut:            %s", cfg["fileOut"])
    logger.info("       fileName:        %s", cfg["fileName"])
    logger.info("    includeForecast:    %s", cfg["includeForecast"])
    logger.info("       url:             %s", cfg["forecast"]["source"]["url"])
    logger.info("       lat:             %s", cfg["forecast"]["source"]["payload"]["lat"])
    logger.info("       lon:             %s", cfg["forecast"]["source"]["payload"]["lon"])
    logger.info("       units:           %s", cfg["forecast"]["source"]["payload"]["units"])
    logger.info("       lang:            %s", cfg["forecast"]["source"]["payload"]["lang"])
    logger.info("       appid:           %s", cfg["forecast"]["source"]["payload"]["appid"])
    logger.info("       forecastDbOut:   %s", cfg["forecast"]["forecastDbOut"])
    logger.info("       forecastFileOut: %s", cfg["forecast"]["forecastFileOut"])
    logger.info("       forecastRetain : %s", cfg["forecast"]["forecastRetain"])
    logger.info("       hourlyForecast:  %s", cfg["forecast"]["forecastTables"]["hourlyForecast"])
    logger.info("       dailyForecast:   %s", cfg["forecast"]["forecastTables"]["dailyForecast"])
    logger.info("       forecastFile:    %s", cfg["forecast"]["forecastFile"])

def waitForNextCycle():
    """
    Wait for next measurement cycle.

    This function assures that measurements are done at specific times depending on the specified interval
    In case that measurementInterval is an integer multiple of 60, the waiting time is calculated in a way,
    that one measurement is done every full hour.
    """
    global cfg

    if (cfg["measurementInterval"] % 60 == 0)\
    or (cfg["measurementInterval"] % 120 == 0)\
    or (cfg["measurementInterval"] % 240 == 0)\
    or (cfg["measurementInterval"] % 300 == 0)\
    or (cfg["measurementInterval"] % 360 == 0)\
    or (cfg["measurementInterval"] % 600 == 0)\
    or (cfg["measurementInterval"] % 720 == 0)\
    or (cfg["measurementInterval"] % 900 == 0)\
    or (cfg["measurementInterval"] % 1200 == 0)\
    or (cfg["measurementInterval"] % 1800 == 0):
        tNow = datetime.datetime.now()
        seconds = 60 * tNow.minute
        period = math.floor(seconds/cfg["measurementInterval"])
        waitTimeSec = (period + 1) * cfg["measurementInterval"] - (60 * tNow.minute + tNow.second + tNow.microsecond / 1000000)
        logger.debug("At %s waiting for %s sec.", datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S,"), waitTimeSec)
        time.sleep(waitTimeSec)
    elif (cfg["measurementInterval"] % 2 == 0)\
      or (cfg["measurementInterval"] % 4 == 0)\
      or (cfg["measurementInterval"] % 5 == 0)\
      or (cfg["measurementInterval"] % 6 == 0)\
      or (cfg["measurementInterval"] % 10 == 0)\
      or (cfg["measurementInterval"] % 12 == 0)\
      or (cfg["measurementInterval"] % 15 == 0)\
      or (cfg["measurementInterval"] % 20 == 0)\
      or (cfg["measurementInterval"] % 30 == 0):
            tNow = datetime.datetime.now()
            seconds = 60 * tNow.minute + tNow.second
            period = math.floor(seconds/cfg["measurementInterval"])
            waitTimeSec = (period + 1) * cfg["measurementInterval"] - seconds
            logger.debug("At %s waiting for %s sec.", datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S,"), waitTimeSec)
            time.sleep(waitTimeSec)
    else:
        waitTimeSec =cfg["measurementInterval"]
        logger.debug("At %s waiting for %s sec.", datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S,"), waitTimeSec)
        time.sleep(waitTimeSec)

def pressureReduced(p, h, t):
    """
    Calculate reducet atmospheric pressure according to Barometric formula.

    Source: https://de.wikipedia.org/wiki/Barometrische_H%C3%B6henformel
    Input:
    p: pressure at height h (in hPa)
    h: height of measurement station in m
    t: Temperature in °C
    """
    import math

    # Constants
    g0 = 9.80665    # Gravitational acceleration (m/s**2)
    R  = 287.05     # Universal gas constant (m**2/s**2 K)
    t0 = 273.15     # Absolute temperature 0°C (K)
    a  = 0.0065     # Vertical temperature gradient
    C  = 0.12       # Parameter for consideration of vapor pressure
    tl = 9.1        # Temperature threshold for approximation of vapor pressure (°C)

    p0 = p
    if h and t:
        if t < tl:
            E = 5.6402 * (-0.0916 + math.exp(0.06 * t))
        else:
            E = 18.2194 * (1.0463 - math.exp(-0.0666 * t))

        x = g0 * h / (R * (t + t0 + C * E + a * h / 2))

        p0 = p * math.exp(x)

    logger.debug("p0(p=%s, h=%s, t=%s) = %s", p, h, t, p0)

    return p0

#============================================================================================
# Start __main__
#============================================================================================
#
# Get Command line options
getCl()

logger.info("=============================================================")
logger.info("Weatherstation started")
logger.info("=============================================================")

# Get configuration
getConfig()

# Database connection, if required
con = None
if cfg["dbOut"]:
    try:
        con = mariadb.connect(
            user=cfg["dbConnection"]["user"],
            password=cfg["dbConnection"]["password"],
            host=cfg["dbConnection"]["host"],
            port=cfg["dbConnection"]["port"],
            database=cfg["dbConnection"]["database"]
        )
        logger.debug("Database connection successful")

    except mariadb.Error as e:
        print("Error connecting to MariaDB: {e}")
        sys.exit(1)

    # Get DB cursor
    cur = con.cursor()

# Instantiate sensor
if cfg["sensorType"] == EnvironmentSensor.type_BME280_I2C:
    sensor = EnvironmentSensor.BME280_I2C()
if cfg["sensorType"] == EnvironmentSensor.type_BME280_SPI:
    sensor = EnvironmentSensor.BME280_SPI(cfg["raspiPinObj"])
if cfg["sensorType"] == EnvironmentSensor.type_DHT11:
    sensor = EnvironmentSensor.DHT11(cfg["raspiPinObj"])
if cfg["sensorType"] == EnvironmentSensor.type_DHT22:
    sensor = EnvironmentSensor.DHT22(cfg["raspiPinObj"])

logger.debug("Sensor instantiated: %s", cfg["sensorType"])

# Open output file
f = None
if cfg["fileOut"]:
    fn = cfg["fileName"]
    f = open(fn, 'w')
    logger.debug("File opened: %s", fn)

# Open file for forecast output
fcf = None
if cfg["forecast"]["forecastFileOut"]:
    fn = cfg["forecast"]["forecastFile"]
    fcf = open(fn, 'w')
    logger.debug("File opened: %s", fn)

    fcf.write('{"forecast": [')

noWait = False
stop = False

while not stop:
    try:
        # Wait unless noWait is set in case of sensor error.
        # Akip waiting for test run
        if not noWait and not testRun:
            waitForNextCycle()
        noWait = False

        # Prepare database statement
        curDateTime  = datetime.datetime.now()
        curTimestamp = curDateTime.strftime("%Y-%m-%d %H:%M:%S")
        curDate      = curDateTime.strftime("%Y-%m-%d")
        curTime      = curDateTime.strftime("%H:%M:%S")
        txt = curTimestamp
        ins1 = "INSERT INTO " + cfg["dbConnection"]["table"] + " (timestamp, date, time"
        ins2 = "VALUES ('"  + curTimestamp + "', '" + curDate + "', '" + curTime + "'"

        # Get temperature from sensor
        temperature = sensor.temperature
        if temperature is None:
            txt = txt + ","
        else:
            txt = txt + "{:+.1f},".format(temperature)
            ins1 = ins1 + ", temperature"
            ins2 = ins2 + ", " + "{:+.1f}".format(temperature)

        # Get humidity from sensor
        humidity = sensor.humidity
        if humidity is None:
            txt = txt + ","
        else:
            txt = txt + "{:.1f},".format(humidity)
            ins1 = ins1 + ", humidity"
            ins2 = ins2 + ", " + "{:+.1f}".format(humidity)

        # Get pressure from sensor
        pressure = sensor.pressure
        if pressure is None:
            txt = txt + ","
        else:
            txt = txt + "{:.1f},".format(pressure)
            ins1 = ins1 + ", pressure_m"
            ins2 = ins2 + ", " + "{:+.1f}".format(pressure)
            pressure_r = pressureReduced(pressure, cfg["height"], temperature)
            txt = txt + "{:.1f},".format(pressure_r)
            ins1 = ins1 + ", pressure"
            ins2 = ins2 + ", " + "{:+.1f}".format(pressure_r)

        # Get altitude from sensor
        altitude = sensor.altitude
        if pressure is None:
            txt = txt + ","
        else:
            txt = txt + "{:.1f}".format(altitude)
            ins1 = ins1 + ", altitude"
            ins2 = ins2 + ", " + "{:+.1f}".format(altitude)

        txt = txt + "\n"
        
        # Write to file, if required
        if cfg["fileOut"]:
            f.write(txt)

        # Log measurement
        if servRun:
            logger.debug("Measurement: %s", txt)
        else:
            logger.info("Measurement: %s", txt)

        # Insert into database, if required
        if cfg["dbOut"]:
            ins = ins1 + ") " + ins2 + ")"
            logger.debug(ins)
            cur.execute(ins)
            con.commit()

        # Get forecast
        if cfg["includeForecast"]:
            weatherForecastOWM.handleForecast(cfg, curTimestamp, curDate, curTime, con, cur, fcf, servRun)

        if testRun:
            # Stop in case of test run
            stop = True

    except mariadb.Error as e:
        logger.error("MariaDB Error: %s", e.msg)
        if f:
            f.close()
        if fcf:
            fcf.write(']}')
            fcf.close
        if con:
            con.close()
        raise e

    except RuntimeError as error:
        # Errors happen fairly often, DHT's are hard to read, just keep going
        if not servRun:
            logger.error("Ignored RuntimeError: %s", error.args[0])

        noWait = True
        if testRun:
            # Stop in case of test run
            stop = True
        else:
            time.sleep(2.0)
            continue

    except Exception as error:
        del sensor
        if f:
            f.close()
        if fcf:
            fcf.write(']}')
            fcf.close
        if con:
            con.close()
        raise error

    except KeyboardInterrupt:
        if sensor:
            del sensor
        if f:
            f.close()
        if fcf:
            fcf.write(']}')
            fcf.close
        if con:
            con.close()

if con:
    con.close()
if sensor:
    del sensor
if f:
    f.close()
if fcf:
    fcf.write(']}')
    fcf.close

logger.info("=============================================================")
logger.info("Weatherstation terminated")
logger.info("=============================================================")
