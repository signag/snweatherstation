CREATE TABLE `weatherdata` (
	`timestamp` TIMESTAMP NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
	`date` DATE NOT NULL,
	`time` TIME NOT NULL,
	`temperature` FLOAT NULL DEFAULT NULL,
	`humidity` FLOAT NULL DEFAULT NULL,
	`pressure` FLOAT NULL DEFAULT NULL,
	`altitude` FLOAT NULL DEFAULT NULL,
	PRIMARY KEY (`timestamp`) USING BTREE
)
COLLATE='utf8_general_ci'
ENGINE=InnoDB
;