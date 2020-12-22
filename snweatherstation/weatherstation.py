#!/usr/bin/python3
"""
Module weatherStation

This module includes functions for a weather station
"""

from snraspi.sensors import EnvironmentSensor
import time
from datetime import datetime
import mariadb
import sys
import math
import os.path
import json

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
    "sensorType": "BME280_I2C",
    "raspiPin": None,
    "raspiPinObj": None,
    "measurementInterval": 2,
    "dbOut": False,
    "fileOut": False,
    "dbConnection":
    {
        "host": None, 
        "port": None, 
        "database": None, 
        "table" : None,
        "user": None, 
        "password": None
    },
    "fileName": None
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
    will be searched under $HOME/.config or /etc.

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

    if args.Log:
        # Deep logging
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        eLogger.addHandler(handler)
        eLogger.setLevel(logging.DEBUG)
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
            if "dbOut" in conf:
                cfg["dbOut"] = conf["dbOut"]
            if "fileOut" in conf:
                cfg["fileOut"] = conf["fileOut"]
            if "dbConnection" in conf:
                if "host" in conf["dbConnection"]:
                    cfg["dbConnection"]["host"] = conf["dbConnection"]["host"]
                if "port" in conf["dbConnection"]:
                    cfg["dbConnection"]["port"] = conf["dbConnection"]["port"]
                if "database" in conf["dbConnection"]:
                    cfg["dbConnection"]["database"] = conf["dbConnection"]["database"]
                if "table" in conf["dbConnection"]:
                    cfg["dbConnection"]["table"] = conf["dbConnection"]["table"]
                if "user" in conf["dbConnection"]:
                    cfg["dbConnection"]["user"] = conf["dbConnection"]["user"]
                if "password" in conf["dbConnection"]:
                    cfg["dbConnection"]["password"] = conf["dbConnection"]["password"]
            if "fileName" in conf:
                cfg["fileName"] = conf["fileName"]

    # Check raspiPin
    pin = cfg["raspiPin"]
    if pin == "":
        if cfg["sensorType"] == EnvironmentSensor.type_BME280_SPI \
        or cfg["sensorType"] == EnvironmentSensor.type_DHT11 \
        or cfg["sensorType"] == EnvironmentSensor.type_DHT22:
            raise ValueError("Configuration file requires raspiPin for sensor type ", cfg["sensorType"])
    if pin == "PIN03":
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
    logger.info("    dbOut:              %s", cfg["dbOut"])
    logger.info("       host:            %s", cfg["dbConnection"]["host"])
    logger.info("       port:            %s", cfg["dbConnection"]["port"])
    logger.info("       database:        %s", cfg["dbConnection"]["database"])
    logger.info("       table:           %s", cfg["dbConnection"]["table"])
    logger.info("       user:            %s", cfg["dbConnection"]["user"])
    logger.info("       password:        %s", cfg["dbConnection"]["password"])
    logger.info("    fileOut:            %s", cfg["fileOut"])
    logger.info("       fileName:        %s", cfg["fileName"])

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
        tNow = datetime.now()
        seconds = 60 * tNow.minute
        period = math.floor(seconds/cfg["measurementInterval"])
        waitTimeSec = (period + 1) * cfg["measurementInterval"] - (60 * tNow.minute + tNow.second + tNow.microsecond / 1000000)
        logger.debug("At %s waiting for %s sec.", datetime.now().strftime("%Y/%m/%d %H:%M:%S,"), waitTimeSec)
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
            tNow = datetime.now()
            seconds = 60 * tNow.minute + tNow.second
            period = math.floor(seconds/cfg["measurementInterval"])
            waitTimeSec = (period + 1) * cfg["measurementInterval"] - seconds
            logger.debug("At %s waiting for %s sec.", datetime.now().strftime("%Y/%m/%d %H:%M:%S,"), waitTimeSec)
            time.sleep(waitTimeSec)
    else:
        waitTimeSec =cfg["measurementInterval"]
        logger.debug("At %s waiting for %s sec.", datetime.now().strftime("%Y/%m/%d %H:%M:%S,"), waitTimeSec)
        time.sleep(waitTimeSec)

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

f = None
if cfg["fileOut"]:
    fn = cfg["fileName"]
    f = open(fn, 'a+')
    logger.debug("File opened: %s", cfg["fileName"])

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
        txt = datetime.now().strftime("%Y/%m/%d,%H:%M:%S,")
        ins1 = "INSERT INTO " + cfg["dbConnection"]["table"] + " (timestamp, date, time"
        ins2 = "VALUES ('"  + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "', '" + datetime.now().strftime("%Y-%m-%d") + "', '" + datetime.now().strftime("%H:%M:%S") + "'"

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
            ins1 = ins1 + ", pressure"
            ins2 = ins2 + ", " + "{:+.1f}".format(pressure)

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

        if testRun:
            # Stop in case of test run
            stop = True

    except mariadb.Error as e:
        logger.error("MariaDB Error: %s", e.msg)
        if f:
            f.close()
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
        if con:
            con.close()
        raise error

    except KeyboardInterrupt:
        if sensor:
            del sensor
        if f:
            f.close()
        if con:
            con.close()

if con:
    con.close()
if sensor:
    del sensor
if f:
    f.close()

logger.info("=============================================================")
logger.info("Weatherstation terminated")
logger.info("=============================================================")
