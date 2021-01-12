# snweatherstation

Another weather station for Raspberry Pi, logging temperature, humidity and pressure (station height and reduced) in a database table or to a file.
If configured, also foracast data from <https://openweathermap.org/> are logged in the database.

A web application is available at <https://github.com/signag/snweather-ui> to visualize measured data together with historical and forecast data.

## Getting started

| Step | Action                                                                                                        |
|------|---------------------------------------------------------------------------------------------------------------|
| 1.   | Install **snweatherstation** (```[sudo] pip install snweatherstation```)                                      |
| 2.   | Connect the chosen sensor to the Raspberry Pi GPIO pins (see [Supported Sensor Types](#supportedsensortypes)) |
| 3.   | Create a new MariaDB database or select an available one (see [MariaDB](#mariadb) below)                      |
| 4.   | Create table for weather data (see [Database Schema Setup](#databaseschemasetup))                             |
| 5.   | If forecast data are intended, create also the database tables for forecast data                              |
| 6.   | Stage and configure the configuration file (see [Configuration](#configuration))                              |
| 7.   | Do a test run (see [Usage](#usage))                                                                           |
| 8.   | Set up Weatherstation service (see [Configure Weatherstation Service](#configureweatherstationservice))       |

## Usage

```shell
usage: weatherstation.py [-h] [-t] [-s] [-l] [-L] [-F] [-f FILE] [-v]
                         [-c CONFIG]

    This program periodically reads environment sensor data
    and stores these either in the database and/or in a file and/or just prints measured values.

    If not otherwise specified on the command line, a configuration file
       weatherstation.json
    will be searched under $HOME/.config or under /etc.

    This configuration file specifies the database connection and other runtime parameters.


optional arguments:
  -h, --help            show this help message and exit
  -t, --test            Test run - single cycle - no wait
  -s, --service         Run as service - special logging
  -l, --log             Shallow (module) logging
  -L, --Log             Deep logging
  -F, --Full            Full logging
  -f FILE, --file FILE  Logging configuration from specified JSON dictionary file
  -v, --verbose         Verbose - log INFO level
  -c CONFIG, --config CONFIG
                        Path to config file to be used
```

## Configuration

Configuration for **weatherstation** needs to be provided in a specific configuration file.
By default, a configuration file "weatherstation.json" is searched under ```$HOME/.config``` or under ```/etc```.

For testing in a development environment, primarily the location ```../tests/data``` is searched for a configuration file.

Alternatively, the path to the configuration file can be specified on the command line.

### Inclusion of weatherforecast data

**weatherstation** can record foracast data for the geographic position of the weather station in order to be visualized together with measured data.
Currently, only the service from <https://openweathermap.org/> is supported.
In order to be able to request data from this site, it is necessary to create an account (which is free) and to generate an API key.
The service is free for a limited number of requests (60) per second, which will never be exceeded by **weatherstation**.

### Structure of JSON Configuration File

The following is an example of a configuration file:

```json
{
    "sensorType": "DHT22",
    "raspiPin": "PIN13",
    "measurementInterval": 900,
    "height": 226,
    "dbOut": true,
    "fileOut": false,
    "includeForecast": true,
    "dbConnection":
    {
        "host": "localhost", 
        "port": 3307, 
        "database": "weather", 
        "table": "weatherdata",
        "user": "testuser", 
        "password": "$[TestUser-1]@?"
    },
    "fileName": "weatherData.txt",
    "forecast":
    {
        "source":
        {
            "url": "https://api.openweathermap.org/data/2.5/onecall",
            "payload":
            {
                "lat"   : "54.188055",
                "lon"   : "7.869444",
                "units" : "metric",
                "lang"  : "de",
                "appid" : "xxxxx"
            }
        },
        "forecastDbOut": true,
        "forecastFileOut": false,
        "forecastRetain" : 4,
        "forecastTables":
        {
            "hourlyForecast": "weatherforecast",
            "dailyForecast" : "dailyforecast",
            "alertsForecast": "alerts"
        },
        "forecastFile": "forecastData.txt"
    }
}
```

### Parameters

| Parameter            | Description                                                                            | Mandatory                |
|----------------------|----------------------------------------------------------------------------------------|--------------------------|
| sensorType           | Type of the environment sensor (see supported sensor types, below)                     | Yes                      |
| raspiPin             | Raspberry Pi GPIO pin in BOARD notation used for data signal, if required              | See SesorType            |
| measurementInterval  | Measurement interval in seconds.                                                       | Yes                      |
| height               | Height of weatherstation above sea level (for barometric formula)                      | Yes                      |
| dbOut                | Specifies whether measured values shall be stored in the database (true, false)        | Yes                      |
| fileOut              | Specifies whether measured values shall be written to the specified file (true, false) | Yes                      |
| includeForecast      | Specifies whether forecast data shall be tracked (true, false)                         | Yes                      |
| **dbConnection**     | Database connection parameters                                                         | For dbOut=true           |
| - host               | Host name or IP address of database server                                             | Yes                      |
| - port               | Port for MariaDB service                                                               | Yes                      |
| - database           | Name of the database where data shall be stored                                        | Yes                      |
| - table              | Name of database table where data shall be stored                                      | Yes                      |
| - user               | Database user                                                                          | Yes                      |
| - password           | Password for database user                                                             | Yes                      |
| fileName             | Path to file to which data shall be written (optional)                                 | For fileOut=true         |
| **forecast**         | Parameters for forecast                                                                | For includeForecast=true |
| - **source**         | Parameters for forecast source                                                         | Yes                      |
| -- url               | URL of forecast service provider (currently only <https://openweathermap.org/>)        | No                       |
| -- **payload**       | Service call parameters                                                                | Yes                      |
| --- lat              | Geographical coordinates of the location of the weatherstation (latitude)              | Yes                      |
| --- lon              | Geographical coordinates of the location of the weatherstation (longitude)             | Yes                      |
| --- units            | Units in which to return data ('**metric**' or 'imperial')                             | No                       |
| --- lang             | valid language code for language specific data (default: 'de')                         | No                       |
| --- appid            | Your unique API key (<https://openweathermap.org/> account page under  "API key" tab)  | Yes                      |
| -- forecastDbOut     | If foracast data shall be stored in the database (true, false)                         | Yes                      |
| -- forecastFileOut   | If forecast data shall be written to file (true, false)                                | Yes                      |
| -- forecastRetain    | Number of hours to retain future forecast as historical forecast (default: 4)          | No                       |
| -- **forecastTables**| Table names for forecast data                                                          | For forecastDbOut=true   |
| --- hourlyForecast   | Table name for hourly forecast                                                         | Yes                      |
| --- dailyForecast    | Table name for daily forecast                                                          | Yes                      |
| --- alertsForecast   | Table name for alerts                                                                  | Yes                      |
| -- forecastFile      | Path to file for forecast data. File output is JSON as received from weather service   | For forecastFileOut=true |

### Supported Sensor Types

See also <https://github.com/signag/snraspi-lib/blob/main/docs/EnvironmentSensors.md>

| SensorType | Description  | Measured Data                   | Raspi bus | raspiPin    |
|------------|--------------|---------------------------------|-----------|-------------|
| DHT11      | DHT11        | temperature, humidity           | 1-Wire    | 1-Wire pin  |
| DHT22      | DHT22        | temperature, humidity           | 1-Wire    | 1-Wire pin  |
| BME280_I2C | BME280       | temperature, humidity, pressure | I2C       | --          |
| BMP280_SPI | BME280       | temperature, humidity, pressure | SPI       | Chip Select |

## MariaDB

**weatherstation** stores weather data in a MariaDB database (see <https://mariadb.org/>).

MariaDB is available on Linux and Windows platforms.
A MariaDB server is also provided as plugin on most of the popular NAS systems.
For **weatherstation**, you may use any of your available MariaDB servers, as long as it is visible to your Raspberry Pi.

Alternatively, you may also install a MariaDB server on your Raspberry Pi.

**NOTE** MariaDB Client and connectors are installed together with **weatherstation**.

### Setup MariaDB Server on Raspberry Pi

**INFO** Skip this step if you will be using an existing MariaDB server

#### Installation

```shell
sudo apt install mariadb-server php-mysql
sudo apt install phpmyadmin
```

#### Service configuration

For automatic start:

```shell
sudo systemctl enable mariadb
```

For manual start:

```shell
sudo systemctl disable mariadb

sudo systemctl start mariadb
sudo systemctl stop mariadb
```

#### Database Schema Setup

**weatherstation** requires a database table with a specific structure.
For forecast data, two additional tables are required.

An SQL script template is available under ```./data```: **createDBtable.sql** in the installation folder.

The table names can be adjusted in the script and configured in the **weatherstation** config file so that different tables can be used to distinguish different physical weather stations in the same database.

Run this SQL script against the database to create the required database table(s).

## Configure Weatherstation Service

To continuously log weather data, **weatherstation** should be run as service.

See <https://www.raspberrypi.org/documentation/linux/usage/systemd.md>

A service configuration file template can be found under
```./data``` in the installation folder.
