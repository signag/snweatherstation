CREATE TABLE `weatherdata` (
	`timestamp` TIMESTAMP NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT 'Time',
	`date` DATE NOT NULL COMMENT 'Date',
	`time` TIME NOT NULL COMMENT 'Time',
	`temperature` FLOAT NULL DEFAULT NULL COMMENT 'Temperature in °C',
	`humidity` FLOAT NULL DEFAULT NULL COMMENT 'Humidity in %',
	`pressure` FLOAT NULL DEFAULT NULL COMMENT 'Atmospheric pressure in hPa',
	`altitude` FLOAT NULL DEFAULT NULL COMMENT 'Altitude',
	PRIMARY KEY (`timestamp`) USING BTREE
)
COLLATE='utf8_general_ci'
ENGINE=InnoDB
;
CREATE TABLE `weatherforecast` (
	`timestamp` TIMESTAMP NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT 'Forecast time',
	`temperature` FLOAT NULL DEFAULT NULL COMMENT 'Temperature in °C',
	`humidity` FLOAT NULL DEFAULT NULL COMMENT 'Humidity in %',
	`pressure` FLOAT NULL DEFAULT NULL COMMENT 'Atmospheric pressure in hPa',
	`clouds` FLOAT NULL DEFAULT NULL COMMENT 'Cloudiness in %',
	`uvi` FLOAT NULL DEFAULT NULL COMMENT 'UV index',
	`visibility` FLOAT NULL DEFAULT NULL COMMENT 'Visibility in m',
	`windspeed` FLOAT NULL DEFAULT NULL COMMENT 'Wind speed in m/s',
	`winddir` FLOAT NULL DEFAULT NULL COMMENT 'Wind direction in degrees (meteorological)',
	`rain` FLOAT NULL DEFAULT NULL COMMENT 'Rain volume per hour in mm',
	`snow` FLOAT NULL DEFAULT NULL COMMENT 'Snow volume per hour in mm',
	`description` VARCHAR(50) NULL DEFAULT NULL COMMENT 'Weather condition in default language' COLLATE 'utf8_general_ci',
	`icon` CHAR(3) NULL DEFAULT NULL COMMENT 'ID of weather icon' COLLATE 'utf8_general_ci'
)
COLLATE='utf8_general_ci'
ENGINE=InnoDB
;
CREATE TABLE `dailyforecast` (
	`date` DATE NOT NULL COMMENT 'Forecast date',
	`sunrise` TIME NULL DEFAULT NULL COMMENT 'Sunrise local time',
	`sunset` TIME NULL DEFAULT NULL COMMENT 'Sunset local time',
	`temperature_m` FLOAT NULL DEFAULT NULL COMMENT 'Average temperature morning',
	`temperature_d` FLOAT NULL DEFAULT NULL COMMENT 'Average temperature day',
	`temperature_e` FLOAT NULL DEFAULT NULL COMMENT 'Average temperature evening',
	`temperature_n` FLOAT NULL DEFAULT NULL COMMENT 'Average temperature night',
	`temperature_min` FLOAT NULL DEFAULT NULL COMMENT 'Minimum temperature',
	`temperature_max` FLOAT NULL DEFAULT NULL COMMENT 'Maximum temperature',
	`pressure` FLOAT NULL DEFAULT NULL COMMENT 'Atmospheric pressure in hPa',
	`humidity` FLOAT NULL DEFAULT NULL COMMENT 'Humidity in %',
	`windspeed` FLOAT NULL DEFAULT NULL COMMENT 'Wind speed in m/s',
	`winddir` FLOAT NULL DEFAULT NULL COMMENT 'Wind direction in degrees',
	`clouds` FLOAT NULL DEFAULT NULL COMMENT 'Cloudiness in %',
	`uvi` FLOAT NULL DEFAULT NULL COMMENT 'UV index',
	`pop` FLOAT NULL DEFAULT NULL COMMENT 'Probability of precipitation',
	`rain` FLOAT NULL DEFAULT NULL COMMENT 'Rain volume in mm/h',
	`snow` FLOAT NULL DEFAULT NULL COMMENT 'Snow volume in mm/h',
	`description` VARCHAR(50) NULL DEFAULT NULL COMMENT 'weather condition' COLLATE 'utf8_general_ci',
	`icon` VARCHAR(3) NULL DEFAULT NULL COMMENT 'Weather icon ID' COLLATE 'utf8_general_ci'
)
COLLATE='utf8_general_ci'
ENGINE=InnoDB
;
