-- ============================================================================
-- Phase 2: Synthetic Data Generation
-- Predictive Maintenance & OEE Command Center
-- Domain-grounded in real vibration management (MachPulse-style)
-- ISO 10816 vibration severity standards
-- ============================================================================

USE ROLE ACCOUNTADMIN;
USE WAREHOUSE PM_WH;
USE DATABASE PREDICTIVE_MAINTENANCE;
USE SCHEMA RAW;

-- ============================================================================
-- 2.1  PLANTS (3 plants)
-- ============================================================================
CREATE OR REPLACE TABLE PLANTS (
    PLANT_ID        VARCHAR(20)   NOT NULL,
    PLANT_NAME      VARCHAR(100)  NOT NULL,
    LOCATION        VARCHAR(100),
    REGION          VARCHAR(50),
    PLANT_TYPE      VARCHAR(50),
    COMMISSIONED    DATE,
    TIMEZONE        VARCHAR(50),
    PRIMARY KEY (PLANT_ID)
);

INSERT INTO PLANTS VALUES
    ('PLT-001', 'Atul Chemicals - Valsad',     'Valsad, Gujarat',      'West',  'Chemical Processing', '2008-03-15', 'Asia/Kolkata'),
    ('PLT-002', 'Vapi Polymers Unit',           'Vapi, Gujarat',        'West',  'Polymer Manufacturing','2012-07-22', 'Asia/Kolkata'),
    ('PLT-003', 'Ankleshwar Pharma Complex',    'Ankleshwar, Gujarat',  'West',  'Pharmaceutical',      '2015-11-10', 'Asia/Kolkata');

-- ============================================================================
-- 2.2  AREAS (functional areas within each plant)
-- ============================================================================
CREATE OR REPLACE TABLE AREAS (
    AREA_ID     VARCHAR(20)   NOT NULL,
    PLANT_ID    VARCHAR(20)   NOT NULL,
    AREA_NAME   VARCHAR(100)  NOT NULL,
    AREA_CODE   VARCHAR(10),
    PRIMARY KEY (AREA_ID),
    FOREIGN KEY (PLANT_ID) REFERENCES PLANTS(PLANT_ID)
);

INSERT INTO AREAS VALUES
    ('AREA-001', 'PLT-001', 'Utility Block',          'UTL'),
    ('AREA-002', 'PLT-001', 'Refrigeration Section',   'REF'),
    ('AREA-003', 'PLT-001', 'Cooling Water System',    'CWS'),
    ('AREA-004', 'PLT-001', 'Process Block A',         'PBA'),
    ('AREA-005', 'PLT-002', 'Compressor House',        'CMH'),
    ('AREA-006', 'PLT-002', 'Extrusion Line',          'EXT'),
    ('AREA-007', 'PLT-002', 'Cooling Tower',           'CLT'),
    ('AREA-008', 'PLT-002', 'Raw Material Handling',   'RMH'),
    ('AREA-009', 'PLT-003', 'HVAC Section',            'HVC'),
    ('AREA-010', 'PLT-003', 'Solvent Recovery',        'SLV'),
    ('AREA-011', 'PLT-003', 'Reactor Utilities',       'RCU'),
    ('AREA-012', 'PLT-003', 'Water Treatment',         'WTP');

-- ============================================================================
-- 2.3  ASSET_GROUPS (equipment trains / functional groupings)
-- ============================================================================
CREATE OR REPLACE TABLE ASSET_GROUPS (
    GROUP_ID    VARCHAR(20)   NOT NULL,
    AREA_ID     VARCHAR(20)   NOT NULL,
    GROUP_NAME  VARCHAR(100)  NOT NULL,
    GROUP_CODE  VARCHAR(10),
    CRITICALITY VARCHAR(10),  -- A (critical), B (essential), C (general purpose)
    PRIMARY KEY (GROUP_ID),
    FOREIGN KEY (AREA_ID) REFERENCES AREAS(AREA_ID)
);

INSERT INTO ASSET_GROUPS VALUES
    -- PLT-001 groups
    ('GRP-001', 'AREA-002', 'Freon Compressor Group 510',  '510', 'A'),
    ('GRP-002', 'AREA-002', 'Freon Compressor Group 520',  '520', 'A'),
    ('GRP-003', 'AREA-001', 'Blower Group 731',            '731', 'B'),
    ('GRP-004', 'AREA-003', 'CW Pump Set 310',             '310', 'A'),
    ('GRP-005', 'AREA-004', 'Process Pump Set 410',        '410', 'B'),
    -- PLT-002 groups
    ('GRP-006', 'AREA-005', 'Air Compressor Group 610',    '610', 'A'),
    ('GRP-007', 'AREA-005', 'Air Compressor Group 620',    '620', 'A'),
    ('GRP-008', 'AREA-006', 'Extruder Drive Group 710',    '710', 'A'),
    ('GRP-009', 'AREA-007', 'CT Fan Group 810',            '810', 'B'),
    ('GRP-010', 'AREA-008', 'Conveyor Drive Group 910',    '910', 'C'),
    -- PLT-003 groups
    ('GRP-011', 'AREA-009', 'AHU Blower Group 130',        '130', 'B'),
    ('GRP-012', 'AREA-010', 'Vacuum Pump Set 230',         '230', 'A'),
    ('GRP-013', 'AREA-011', 'Chilled Water Pump Set 330',  '330', 'A'),
    ('GRP-014', 'AREA-011', 'Reactor Agitator Group 430',  '430', 'A'),
    ('GRP-015', 'AREA-012', 'WTP Blower Group 530',        '530', 'B');

-- ============================================================================
-- 2.4  ASSETS (~75 assets: motors, compressors, blowers, pumps, fans)
-- ============================================================================
CREATE OR REPLACE TABLE ASSETS (
    ASSET_ID        VARCHAR(20)   NOT NULL,
    GROUP_ID        VARCHAR(20)   NOT NULL,
    ASSET_NAME      VARCHAR(50)   NOT NULL,   -- e.g. 'MTR 510 A'
    ASSET_TYPE      VARCHAR(20)   NOT NULL,   -- MOTOR, COMPRESSOR, BLOWER, PUMP, FAN
    MACHINE_CLASS   VARCHAR(10),              -- ISO 10816 class: I, II, III, IV
    RATED_RPM       INT,
    RATED_POWER_KW  FLOAT,
    INSTALL_DATE    DATE,
    MANUFACTURER    VARCHAR(50),
    MODEL_NUMBER    VARCHAR(50),
    PRIMARY KEY (ASSET_ID),
    FOREIGN KEY (GROUP_ID) REFERENCES ASSET_GROUPS(GROUP_ID)
);

-- Generate assets programmatically using a helper approach
-- PLT-001: Freon compressors (510 A/B/C), (520 A/B/C), Blowers (731 A/B), CW Pumps (310 A/B/C), Process Pumps (410 A/B)
-- PLT-002: Air compressors (610 A/B/C), (620 A/B), Extruder drives (710 A/B), CT Fans (810 A/B/C/D), Conveyor drives (910 A/B)
-- PLT-003: AHU Blowers (130 A/B), Vacuum pumps (230 A/B/C), CW Pumps (330 A/B), Agitators (430 A/B/C), WTP Blowers (530 A/B)

INSERT INTO ASSETS VALUES
    -- ===== PLT-001: Atul Chemicals =====
    -- Freon Compressor Group 510 (motor + compressor × 3 trains)
    ('A-001', 'GRP-001', 'MTR 510 A',   'MOTOR',      'III', 1480, 110, '2010-05-12', 'Siemens',    '1LE1501-2AB53'),
    ('A-002', 'GRP-001', 'COMP 510 A',  'COMPRESSOR', 'III', 1480, NULL, '2010-05-12', 'Bitzer',     '6HE-28Y'),
    ('A-003', 'GRP-001', 'MTR 510 B',   'MOTOR',      'III', 1480, 110, '2010-05-12', 'Siemens',    '1LE1501-2AB53'),
    ('A-004', 'GRP-001', 'COMP 510 B',  'COMPRESSOR', 'III', 1480, NULL, '2010-05-12', 'Bitzer',     '6HE-28Y'),
    ('A-005', 'GRP-001', 'MTR 510 C',   'MOTOR',      'III', 1480, 110, '2011-02-20', 'ABB',        'M3BP 280SMB 4'),
    ('A-006', 'GRP-001', 'COMP 510 C',  'COMPRESSOR', 'III', 1480, NULL, '2011-02-20', 'Bitzer',     '6HE-28Y'),
    -- Freon Compressor Group 520
    ('A-007', 'GRP-002', 'MTR 520 A',   'MOTOR',      'III', 2960, 160, '2013-08-15', 'ABB',        'M3BP 315SMA 2'),
    ('A-008', 'GRP-002', 'COMP 520 A',  'COMPRESSOR', 'III', 2960, NULL, '2013-08-15', 'Bitzer',     'CSH8573-110Y'),
    ('A-009', 'GRP-002', 'MTR 520 B',   'MOTOR',      'III', 2960, 160, '2013-08-15', 'Siemens',    '1LE1604-2BB23'),
    ('A-010', 'GRP-002', 'COMP 520 B',  'COMPRESSOR', 'III', 2960, NULL, '2013-08-15', 'Bitzer',     'CSH8573-110Y'),
    ('A-011', 'GRP-002', 'MTR 520 C',   'MOTOR',      'III', 2960, 160, '2014-01-10', 'ABB',        'M3BP 315SMA 2'),
    ('A-012', 'GRP-002', 'COMP 520 C',  'COMPRESSOR', 'III', 2960, NULL, '2014-01-10', 'Bitzer',     'CSH8573-110Y'),
    -- Blower Group 731
    ('A-013', 'GRP-003', 'MTR 731 A',   'MOTOR',      'II',  2960, 55,  '2012-03-18', 'Crompton',   'GD-280S'),
    ('A-014', 'GRP-003', 'BLWR 731 A',  'BLOWER',     'II',  2960, NULL, '2012-03-18', 'Everest',    'RB-150'),
    ('A-015', 'GRP-003', 'MTR 731 B',   'MOTOR',      'II',  2960, 55,  '2012-03-18', 'Crompton',   'GD-280S'),
    ('A-016', 'GRP-003', 'BLWR 731 B',  'BLOWER',     'II',  2960, NULL, '2012-03-18', 'Everest',    'RB-150'),
    -- CW Pump Set 310
    ('A-017', 'GRP-004', 'MTR 310 A',   'MOTOR',      'III', 1480, 90,  '2009-11-05', 'Siemens',    '1LE1503-2AB'),
    ('A-018', 'GRP-004', 'PUMP 310 A',  'PUMP',       'III', 1480, NULL, '2009-11-05', 'KSB',        'Etanorm 100-080-250'),
    ('A-019', 'GRP-004', 'MTR 310 B',   'MOTOR',      'III', 1480, 90,  '2009-11-05', 'ABB',        'M3BP 280SMA 4'),
    ('A-020', 'GRP-004', 'PUMP 310 B',  'PUMP',       'III', 1480, NULL, '2009-11-05', 'KSB',        'Etanorm 100-080-250'),
    ('A-021', 'GRP-004', 'MTR 310 C',   'MOTOR',      'III', 1480, 90,  '2015-06-20', 'Siemens',    '1LE1503-2AB'),
    ('A-022', 'GRP-004', 'PUMP 310 C',  'PUMP',       'III', 1480, NULL, '2015-06-20', 'KSB',        'Etanorm 100-080-250'),
    -- Process Pump Set 410
    ('A-023', 'GRP-005', 'MTR 410 A',   'MOTOR',      'II',  2960, 37,  '2016-04-10', 'ABB',        'M3BP 200MLA 2'),
    ('A-024', 'GRP-005', 'PUMP 410 A',  'PUMP',       'II',  2960, NULL, '2016-04-10', 'Grundfos',   'CR 32-6'),
    ('A-025', 'GRP-005', 'MTR 410 B',   'MOTOR',      'II',  2960, 37,  '2016-04-10', 'ABB',        'M3BP 200MLA 2'),
    ('A-026', 'GRP-005', 'PUMP 410 B',  'PUMP',       'II',  2960, NULL, '2016-04-10', 'Grundfos',   'CR 32-6'),

    -- ===== PLT-002: Vapi Polymers =====
    -- Air Compressor Group 610
    ('A-027', 'GRP-006', 'MTR 610 A',   'MOTOR',      'III', 1480, 132, '2014-02-28', 'Siemens',    '1LE1604-1EB'),
    ('A-028', 'GRP-006', 'COMP 610 A',  'COMPRESSOR', 'III', 1480, NULL, '2014-02-28', 'Atlas Copco','GA 90'),
    ('A-029', 'GRP-006', 'MTR 610 B',   'MOTOR',      'III', 1480, 132, '2014-02-28', 'ABB',        'M3BP 315SMB 4'),
    ('A-030', 'GRP-006', 'COMP 610 B',  'COMPRESSOR', 'III', 1480, NULL, '2014-02-28', 'Atlas Copco','GA 90'),
    ('A-031', 'GRP-006', 'MTR 610 C',   'MOTOR',      'III', 1480, 132, '2017-09-01', 'Siemens',    '1LE1604-1EB'),
    ('A-032', 'GRP-006', 'COMP 610 C',  'COMPRESSOR', 'III', 1480, NULL, '2017-09-01', 'Atlas Copco','GA 90'),
    -- Air Compressor Group 620
    ('A-033', 'GRP-007', 'MTR 620 A',   'MOTOR',      'III', 2960, 200, '2016-06-15', 'ABB',        'M3BP 315LKA 2'),
    ('A-034', 'GRP-007', 'COMP 620 A',  'COMPRESSOR', 'III', 2960, NULL, '2016-06-15', 'Ingersoll Rand','R110i'),
    ('A-035', 'GRP-007', 'MTR 620 B',   'MOTOR',      'III', 2960, 200, '2016-06-15', 'Siemens',    '1LE1604-2CB'),
    ('A-036', 'GRP-007', 'COMP 620 B',  'COMPRESSOR', 'III', 2960, NULL, '2016-06-15', 'Ingersoll Rand','R110i'),
    -- Extruder Drive Group 710
    ('A-037', 'GRP-008', 'MTR 710 A',   'MOTOR',      'III', 1480, 250, '2013-10-20', 'Siemens',    '1LE1604-3AB'),
    ('A-038', 'GRP-008', 'MTR 710 B',   'MOTOR',      'III', 1480, 250, '2013-10-20', 'ABB',        'M3BP 355SMA 4'),
    -- CT Fan Group 810
    ('A-039', 'GRP-009', 'MTR 810 A',   'MOTOR',      'II',  960,  30,  '2015-01-12', 'Crompton',   'GD-225M'),
    ('A-040', 'GRP-009', 'FAN 810 A',   'FAN',        'II',  960,  NULL, '2015-01-12', 'Paharpur',   'FRP-Induced'),
    ('A-041', 'GRP-009', 'MTR 810 B',   'MOTOR',      'II',  960,  30,  '2015-01-12', 'Crompton',   'GD-225M'),
    ('A-042', 'GRP-009', 'FAN 810 B',   'FAN',        'II',  960,  NULL, '2015-01-12', 'Paharpur',   'FRP-Induced'),
    ('A-043', 'GRP-009', 'MTR 810 C',   'MOTOR',      'II',  960,  30,  '2018-04-05', 'ABB',        'M3BP 225SMA 6'),
    ('A-044', 'GRP-009', 'FAN 810 C',   'FAN',        'II',  960,  NULL, '2018-04-05', 'Paharpur',   'FRP-Induced'),
    ('A-045', 'GRP-009', 'MTR 810 D',   'MOTOR',      'II',  960,  30,  '2018-04-05', 'ABB',        'M3BP 225SMA 6'),
    ('A-046', 'GRP-009', 'FAN 810 D',   'FAN',        'II',  960,  NULL, '2018-04-05', 'Paharpur',   'FRP-Induced'),
    -- Conveyor Drive Group 910
    ('A-047', 'GRP-010', 'MTR 910 A',   'MOTOR',      'II',  1480, 22,  '2017-11-30', 'Siemens',    '1LE1501-1EA'),
    ('A-048', 'GRP-010', 'MTR 910 B',   'MOTOR',      'II',  1480, 22,  '2017-11-30', 'Siemens',    '1LE1501-1EA'),

    -- ===== PLT-003: Ankleshwar Pharma =====
    -- AHU Blower Group 130
    ('A-049', 'GRP-011', 'MTR 130 A',   'MOTOR',      'II',  1480, 45,  '2016-08-22', 'ABB',        'M3BP 250SMA 4'),
    ('A-050', 'GRP-011', 'BLWR 130 A',  'BLOWER',     'II',  1480, NULL, '2016-08-22', 'Everest',    'RB-100'),
    ('A-051', 'GRP-011', 'MTR 130 B',   'MOTOR',      'II',  1480, 45,  '2016-08-22', 'Crompton',   'GD-250S'),
    ('A-052', 'GRP-011', 'BLWR 130 B',  'BLOWER',     'II',  1480, NULL, '2016-08-22', 'Everest',    'RB-100'),
    -- Vacuum Pump Set 230
    ('A-053', 'GRP-012', 'MTR 230 A',   'MOTOR',      'III', 1480, 75,  '2017-03-14', 'Siemens',    '1LE1503-1EA'),
    ('A-054', 'GRP-012', 'PUMP 230 A',  'PUMP',       'III', 1480, NULL, '2017-03-14', 'Busch',      'R5-0630B'),
    ('A-055', 'GRP-012', 'MTR 230 B',   'MOTOR',      'III', 1480, 75,  '2017-03-14', 'ABB',        'M3BP 280SMB 4'),
    ('A-056', 'GRP-012', 'PUMP 230 B',  'PUMP',       'III', 1480, NULL, '2017-03-14', 'Busch',      'R5-0630B'),
    ('A-057', 'GRP-012', 'MTR 230 C',   'MOTOR',      'III', 1480, 75,  '2019-01-08', 'Siemens',    '1LE1503-1EA'),
    ('A-058', 'GRP-012', 'PUMP 230 C',  'PUMP',       'III', 1480, NULL, '2019-01-08', 'Busch',      'R5-0630B'),
    -- Chilled Water Pump Set 330
    ('A-059', 'GRP-013', 'MTR 330 A',   'MOTOR',      'III', 2960, 110, '2016-05-30', 'ABB',        'M3BP 280SMB 2'),
    ('A-060', 'GRP-013', 'PUMP 330 A',  'PUMP',       'III', 2960, NULL, '2016-05-30', 'KSB',        'Etanorm 125-100-315'),
    ('A-061', 'GRP-013', 'MTR 330 B',   'MOTOR',      'III', 2960, 110, '2016-05-30', 'Siemens',    '1LE1604-1EB'),
    ('A-062', 'GRP-013', 'PUMP 330 B',  'PUMP',       'III', 2960, NULL, '2016-05-30', 'KSB',        'Etanorm 125-100-315'),
    -- Reactor Agitator Group 430
    ('A-063', 'GRP-014', 'MTR 430 A',   'MOTOR',      'III', 1480, 55,  '2018-02-14', 'Siemens',    '1LE1503-1DA'),
    ('A-064', 'GRP-014', 'MTR 430 B',   'MOTOR',      'III', 1480, 55,  '2018-02-14', 'ABB',        'M3BP 250SMA 4'),
    ('A-065', 'GRP-014', 'MTR 430 C',   'MOTOR',      'III', 1480, 55,  '2020-06-01', 'Siemens',    '1LE1503-1DA'),
    -- WTP Blower Group 530
    ('A-066', 'GRP-015', 'MTR 530 A',   'MOTOR',      'II',  2960, 37,  '2019-07-20', 'ABB',        'M3BP 200MLA 2'),
    ('A-067', 'GRP-015', 'BLWR 530 A',  'BLOWER',     'II',  2960, NULL, '2019-07-20', 'Everest',    'RB-075'),
    ('A-068', 'GRP-015', 'MTR 530 B',   'MOTOR',      'II',  2960, 37,  '2019-07-20', 'Crompton',   'GD-200L'),
    ('A-069', 'GRP-015', 'BLWR 530 B',  'BLOWER',     'II',  2960, NULL, '2019-07-20', 'Everest',    'RB-075');

-- ============================================================================
-- 2.5  SENSORS (~300 sensors — DE + NDE per asset, 3-axis each)
-- ============================================================================
CREATE OR REPLACE TABLE SENSORS (
    SENSOR_ID       VARCHAR(20)   NOT NULL,
    ASSET_ID        VARCHAR(20)   NOT NULL,
    BLE_MAC         VARCHAR(8),
    SENSOR_LABEL    VARCHAR(80),   -- e.g. 'MTR 510 A | MTR DE'
    MOUNT_LOCATION  VARCHAR(50),   -- 'Motor Drive End', 'Motor Non-Drive End', 'Comp Bearing B1_Coupling side', etc.
    MOUNT_POSITION  VARCHAR(5),    -- 'DE' or 'NDE'
    X_AXIS_TYPE     VARCHAR(15),   -- 'Vertical', 'Horizontal', 'Axial'
    Y_AXIS_TYPE     VARCHAR(15),
    Z_AXIS_TYPE     VARCHAR(15),
    STATUS          VARCHAR(15)   DEFAULT 'Operational',  -- Operational, Disconnected, Faulty
    INSTALLED_DATE  DATE,
    PRIMARY KEY (SENSOR_ID),
    FOREIGN KEY (ASSET_ID) REFERENCES ASSETS(ASSET_ID)
);

-- Generate sensors: 2 per asset (DE + NDE), with realistic axis mappings
-- Using a CTE to auto-generate them
INSERT INTO SENSORS
WITH asset_sensor_gen AS (
    SELECT
        A.ASSET_ID,
        A.ASSET_NAME,
        A.ASSET_TYPE,
        A.INSTALL_DATE,
        pos.POSITION,
        ROW_NUMBER() OVER (ORDER BY A.ASSET_ID, pos.POSITION) AS rn
    FROM ASSETS A,
    (SELECT 'DE' AS POSITION UNION ALL SELECT 'NDE') pos
)
SELECT
    'SNS-' || LPAD(rn::VARCHAR, 4, '0')                              AS SENSOR_ID,
    ASSET_ID,
    SUBSTR(MD5(ASSET_ID || POSITION), 1, 8)                          AS BLE_MAC,
    ASSET_NAME || ' | ' ||
        CASE ASSET_TYPE
            WHEN 'MOTOR' THEN 'MTR'
            WHEN 'COMPRESSOR' THEN 'COMP'
            WHEN 'BLOWER' THEN 'BLWR'
            WHEN 'PUMP' THEN 'PUMP'
            WHEN 'FAN' THEN 'FAN'
        END || ' ' || POSITION                                        AS SENSOR_LABEL,
    CASE
        WHEN ASSET_TYPE = 'MOTOR'      AND POSITION = 'DE'  THEN 'Motor Drive End'
        WHEN ASSET_TYPE = 'MOTOR'      AND POSITION = 'NDE' THEN 'Motor Non-Drive End'
        WHEN ASSET_TYPE = 'COMPRESSOR' AND POSITION = 'DE'  THEN 'Comp Bearing B1_Coupling Side'
        WHEN ASSET_TYPE = 'COMPRESSOR' AND POSITION = 'NDE' THEN 'Comp Bearing B2_Compressor Side'
        WHEN ASSET_TYPE = 'BLOWER'     AND POSITION = 'DE'  THEN 'B1-Coupling Side'
        WHEN ASSET_TYPE = 'BLOWER'     AND POSITION = 'NDE' THEN 'B2-Blower Side'
        WHEN ASSET_TYPE = 'PUMP'       AND POSITION = 'DE'  THEN 'Pump Bearing DE_Coupling Side'
        WHEN ASSET_TYPE = 'PUMP'       AND POSITION = 'NDE' THEN 'Pump Bearing NDE_Impeller Side'
        WHEN ASSET_TYPE = 'FAN'        AND POSITION = 'DE'  THEN 'Fan Bearing DE_Coupling Side'
        WHEN ASSET_TYPE = 'FAN'        AND POSITION = 'NDE' THEN 'Fan Bearing NDE_Fan Side'
    END                                                               AS MOUNT_LOCATION,
    POSITION                                                          AS MOUNT_POSITION,
    -- Axis orientation varies by position (realistic)
    CASE WHEN MOD(rn, 3) = 0 THEN 'Vertical'   WHEN MOD(rn, 3) = 1 THEN 'Horizontal' ELSE 'Axial'     END AS X_AXIS_TYPE,
    CASE WHEN MOD(rn, 3) = 0 THEN 'Horizontal'  WHEN MOD(rn, 3) = 1 THEN 'Axial'      ELSE 'Vertical'  END AS Y_AXIS_TYPE,
    CASE WHEN MOD(rn, 3) = 0 THEN 'Axial'       WHEN MOD(rn, 3) = 1 THEN 'Vertical'   ELSE 'Horizontal' END AS Z_AXIS_TYPE,
    'Operational'                                                     AS STATUS,
    INSTALL_DATE                                                      AS INSTALLED_DATE
FROM asset_sensor_gen;

-- ============================================================================
-- 2.6  ISO_THRESHOLDS (ISO 10816 vibration severity bands)
-- ============================================================================
CREATE OR REPLACE TABLE ISO_THRESHOLDS (
    MACHINE_CLASS   VARCHAR(5)   NOT NULL,
    ZONE            VARCHAR(20)  NOT NULL,  -- A (Good), B (Satisfactory), C (Unsatisfactory), D (Unacceptable)
    VEL_LOWER_MM_S  FLOAT,                  -- RMS velocity lower bound
    VEL_UPPER_MM_S  FLOAT,                  -- RMS velocity upper bound
    ACCEL_LOWER_G   FLOAT,                  -- RMS acceleration lower bound (m/s²)
    ACCEL_UPPER_G   FLOAT,                  -- RMS acceleration upper bound (m/s²)
    TEMP_WARNING_C  FLOAT,                  -- Temperature warning threshold
    TEMP_ALARM_C    FLOAT,                  -- Temperature alarm threshold
    DESCRIPTION     VARCHAR(200)
);

INSERT INTO ISO_THRESHOLDS VALUES
    -- Class I: Small machines (up to 15 kW)
    ('I',   'A_GOOD',           0,    0.71,  0,    2.5,   55, 65, 'Good - newly commissioned or excellent condition'),
    ('I',   'B_SATISFACTORY',   0.71, 1.8,   2.5,  6.3,   55, 65, 'Satisfactory - acceptable for long-term operation'),
    ('I',   'C_UNSATISFACTORY', 1.8,  4.5,   6.3,  16.0,  55, 65, 'Unsatisfactory - not suitable for long-term, remedial action needed'),
    ('I',   'D_UNACCEPTABLE',   4.5,  999,   16.0, 999,   55, 65, 'Unacceptable - damage risk, immediate action required'),
    -- Class II: Medium machines (15-75 kW) or rigidly mounted up to 300 kW
    ('II',  'A_GOOD',           0,    1.12,  0,    4.0,   60, 70, 'Good - newly commissioned or excellent condition'),
    ('II',  'B_SATISFACTORY',   1.12, 2.8,   4.0,  10.0,  60, 70, 'Satisfactory - acceptable for long-term operation'),
    ('II',  'C_UNSATISFACTORY', 2.8,  7.1,   10.0, 25.0,  60, 70, 'Unsatisfactory - not suitable for long-term, remedial action needed'),
    ('II',  'D_UNACCEPTABLE',   7.1,  999,   25.0, 999,   60, 70, 'Unacceptable - damage risk, immediate action required'),
    -- Class III: Large machines on rigid foundations (>300 kW or special)
    ('III', 'A_GOOD',           0,    1.8,   0,    6.3,   65, 75, 'Good - newly commissioned or excellent condition'),
    ('III', 'B_SATISFACTORY',   1.8,  4.5,   6.3,  16.0,  65, 75, 'Satisfactory - acceptable for long-term operation'),
    ('III', 'C_UNSATISFACTORY', 4.5,  11.2,  16.0, 40.0,  65, 75, 'Unsatisfactory - not suitable for long-term, remedial action needed'),
    ('III', 'D_UNACCEPTABLE',   11.2, 999,   40.0, 999,   65, 75, 'Unacceptable - damage risk, immediate action required'),
    -- Class IV: Large machines on soft/flexible foundations
    ('IV',  'A_GOOD',           0,    2.8,   0,    10.0,  70, 80, 'Good - newly commissioned or excellent condition'),
    ('IV',  'B_SATISFACTORY',   2.8,  7.1,   10.0, 25.0,  70, 80, 'Satisfactory - acceptable for long-term operation'),
    ('IV',  'C_UNSATISFACTORY', 7.1,  18.0,  25.0, 63.0,  70, 80, 'Unsatisfactory - not suitable for long-term, remedial action needed'),
    ('IV',  'D_UNACCEPTABLE',   18.0, 999,   63.0, 999,   70, 80, 'Unacceptable - damage risk, immediate action required');

-- ============================================================================
-- 2.7  USERS (plant personnel)
-- ============================================================================
CREATE OR REPLACE TABLE USERS (
    USER_ID     VARCHAR(20)  NOT NULL,
    USER_NAME   VARCHAR(80)  NOT NULL,
    EMAIL       VARCHAR(120),
    ROLE        VARCHAR(30), -- PLANT_MANAGER, MAINT_ENGINEER, VIB_ANALYST, OPERATOR, ADMIN
    PLANT_ID    VARCHAR(20),
    PRIMARY KEY (USER_ID)
);

INSERT INTO USERS VALUES
    ('USR-001', 'Rajesh Patel',      'rajesh.patel@atul.co.in',       'PLANT_MANAGER',   'PLT-001'),
    ('USR-002', 'Shaishav Desai',    'shaishav.desai@atul.co.in',     'MAINT_ENGINEER',  'PLT-001'),
    ('USR-003', 'Meera Wagh',        'meera.wagh@atul.co.in',         'VIB_ANALYST',     'PLT-001'),
    ('USR-004', 'Amit Shah',         'amit.shah@atul.co.in',          'OPERATOR',        'PLT-001'),
    ('USR-005', 'Priya Mehta',       'priya.mehta@vapi-polymers.com', 'PLANT_MANAGER',   'PLT-002'),
    ('USR-006', 'Suresh Reddy',      'suresh.reddy@vapi-polymers.com','MAINT_ENGINEER',  'PLT-002'),
    ('USR-007', 'Kiran Joshi',       'kiran.joshi@vapi-polymers.com', 'VIB_ANALYST',     'PLT-002'),
    ('USR-008', 'Deepak Kumar',      'deepak.kumar@vapi-polymers.com','OPERATOR',        'PLT-002'),
    ('USR-009', 'Anita Sharma',      'anita.sharma@ankl-pharma.com',  'PLANT_MANAGER',   'PLT-003'),
    ('USR-010', 'Vijay Nair',        'vijay.nair@ankl-pharma.com',    'MAINT_ENGINEER',  'PLT-003'),
    ('USR-011', 'Rohit Gupta',       'rohit.gupta@ankl-pharma.com',   'VIB_ANALYST',     'PLT-003'),
    ('USR-012', 'Neha Singh',        'neha.singh@ankl-pharma.com',    'OPERATOR',        'PLT-003'),
    ('USR-013', 'MachPulse System',  'machpulse@forbesmarshall.com',  'ADMIN',           NULL);

-- ============================================================================
-- 2.8  NOTIFICATION_RULES
-- ============================================================================
CREATE OR REPLACE TABLE NOTIFICATION_RULES (
    RULE_ID         VARCHAR(20)  NOT NULL,
    PLANT_ID        VARCHAR(20)  NOT NULL,
    SEVERITY        VARCHAR(10)  NOT NULL,  -- LOW, MEDIUM, HIGH, CRITICAL
    NOTIFY_ROLES    VARCHAR(200),
    NOTIFY_EMAILS   VARCHAR(500),
    PRIMARY KEY (RULE_ID)
);

INSERT INTO NOTIFICATION_RULES VALUES
    ('NR-001', 'PLT-001', 'LOW',      'VIB_ANALYST',                          'meera.wagh@atul.co.in'),
    ('NR-002', 'PLT-001', 'MEDIUM',   'VIB_ANALYST,MAINT_ENGINEER',           'meera.wagh@atul.co.in,shaishav.desai@atul.co.in'),
    ('NR-003', 'PLT-001', 'HIGH',     'VIB_ANALYST,MAINT_ENGINEER,PLANT_MANAGER', 'meera.wagh@atul.co.in,shaishav.desai@atul.co.in,rajesh.patel@atul.co.in'),
    ('NR-004', 'PLT-001', 'CRITICAL', 'VIB_ANALYST,MAINT_ENGINEER,PLANT_MANAGER,ADMIN', 'meera.wagh@atul.co.in,shaishav.desai@atul.co.in,rajesh.patel@atul.co.in,machpulse@forbesmarshall.com'),
    ('NR-005', 'PLT-002', 'LOW',      'VIB_ANALYST',                          'kiran.joshi@vapi-polymers.com'),
    ('NR-006', 'PLT-002', 'MEDIUM',   'VIB_ANALYST,MAINT_ENGINEER',           'kiran.joshi@vapi-polymers.com,suresh.reddy@vapi-polymers.com'),
    ('NR-007', 'PLT-002', 'HIGH',     'VIB_ANALYST,MAINT_ENGINEER,PLANT_MANAGER', 'kiran.joshi@vapi-polymers.com,suresh.reddy@vapi-polymers.com,priya.mehta@vapi-polymers.com'),
    ('NR-008', 'PLT-002', 'CRITICAL', 'VIB_ANALYST,MAINT_ENGINEER,PLANT_MANAGER,ADMIN', 'kiran.joshi@vapi-polymers.com,suresh.reddy@vapi-polymers.com,priya.mehta@vapi-polymers.com,machpulse@forbesmarshall.com'),
    ('NR-009', 'PLT-003', 'LOW',      'VIB_ANALYST',                          'rohit.gupta@ankl-pharma.com'),
    ('NR-010', 'PLT-003', 'MEDIUM',   'VIB_ANALYST,MAINT_ENGINEER',           'rohit.gupta@ankl-pharma.com,vijay.nair@ankl-pharma.com'),
    ('NR-011', 'PLT-003', 'HIGH',     'VIB_ANALYST,MAINT_ENGINEER,PLANT_MANAGER', 'rohit.gupta@ankl-pharma.com,vijay.nair@ankl-pharma.com,anita.sharma@ankl-pharma.com'),
    ('NR-012', 'PLT-003', 'CRITICAL', 'VIB_ANALYST,MAINT_ENGINEER,PLANT_MANAGER,ADMIN', 'rohit.gupta@ankl-pharma.com,vijay.nair@ankl-pharma.com,anita.sharma@ankl-pharma.com,machpulse@forbesmarshall.com');

-- ============================================================================
-- 2.9  FAILURE_INCIDENTS (~50 incidents across 12 months, 3 plants)
--      These define WHEN and HOW equipment fails — sensor data will be
--      generated with degradation patterns leading up to these events
-- ============================================================================
CREATE OR REPLACE TABLE FAILURE_INCIDENTS (
    INCIDENT_ID         VARCHAR(20)   NOT NULL,
    ASSET_ID            VARCHAR(20)   NOT NULL,
    FAILURE_MODE        VARCHAR(30)   NOT NULL,  -- BEARING_DEFECT, MISALIGNMENT, UNBALANCE, LOOSENESS, ELECTRICAL, LUBRICATION
    FAILURE_TIMESTAMP   TIMESTAMP_NTZ NOT NULL,
    ROOT_CAUSE          VARCHAR(200),
    SEVERITY            VARCHAR(10),             -- LOW, MEDIUM, HIGH, CRITICAL
    DOWNTIME_HOURS      FLOAT,
    DESCRIPTION         VARCHAR(500),
    PRIMARY KEY (INCIDENT_ID),
    FOREIGN KEY (ASSET_ID) REFERENCES ASSETS(ASSET_ID)
);

INSERT INTO FAILURE_INCIDENTS VALUES
    -- PLT-001 incidents (compressors, pumps, blowers)
    ('FI-001', 'A-002', 'BEARING_DEFECT',  '2025-10-15 08:30:00', 'Inner race spalling on B1 bearing due to fatigue',         'HIGH',     12,  'COMP 510 A - Sudden increase in NDE acceleration, bearing replaced'),
    ('FI-002', 'A-001', 'MISALIGNMENT',    '2025-11-22 14:15:00', 'Coupling misalignment after maintenance re-assembly',       'MEDIUM',   6,   'MTR 510 A - Elevated 2x RPM on DE, realigned coupling'),
    ('FI-003', 'A-009', 'UNBALANCE',       '2025-12-05 10:00:00', 'Fan blade deposit buildup causing mass imbalance',          'MEDIUM',   4,   'MTR 520 B - High 1x RPM radial, cleaned and balanced'),
    ('FI-004', 'A-004', 'LUBRICATION',     '2026-01-10 06:45:00', 'Grease degradation in compressor bearing B2',               'LOW',      2,   'COMP 510 B - Temperature rising, regreased bearings'),
    ('FI-005', 'A-018', 'BEARING_DEFECT',  '2026-01-28 16:20:00', 'Outer race defect on DE bearing',                           'HIGH',     18,  'PUMP 310 A - Catastrophic vibration spike, bearing replaced'),
    ('FI-006', 'A-014', 'LOOSENESS',       '2026-02-14 11:30:00', 'Foundation bolt loosening on blower DE',                     'MEDIUM',   3,   'BLWR 731 A - Multiple harmonics, bolts retorqued'),
    ('FI-007', 'A-012', 'ELECTRICAL',      '2026-03-02 09:00:00', 'Rotor bar crack developing in compressor motor',             'HIGH',     24,  'COMP 520 C - 2x line frequency peaks, motor rewound'),
    ('FI-008', 'A-020', 'MISALIGNMENT',    '2026-03-18 13:45:00', 'Thermal growth causing misalignment at operating temp',      'MEDIUM',   5,   'PUMP 310 B - Axial vibration elevated, hot alignment performed'),
    ('FI-009', 'A-001', 'BEARING_DEFECT',  '2026-04-05 07:15:00', 'DE bearing cage defect',                                    'HIGH',     14,  'MTR 510 A - Increasing acceleration trend over 3 weeks, bearing replaced'),
    ('FI-010', 'A-010', 'UNBALANCE',       '2026-04-22 15:30:00', 'Coupling element wear causing dynamic imbalance',            'MEDIUM',   4,   'COMP 520 B - 1x dominant, coupling replaced'),
    ('FI-011', 'A-026', 'LUBRICATION',     '2026-05-08 08:00:00', 'Oil contamination in process pump bearing',                  'MEDIUM',   6,   'PUMP 410 B - Temperature spike + broadband acceleration, oil changed'),
    ('FI-012', 'A-005', 'BEARING_DEFECT',  '2026-06-15 10:30:00', 'Ball defect in NDE bearing',                                'HIGH',     10,  'MTR 510 C - BPFO frequency visible in spectrum, bearing replaced'),
    ('FI-013', 'A-022', 'LOOSENESS',       '2026-07-01 14:00:00', 'Pump impeller clearance loose',                              'LOW',      3,   'PUMP 310 C - Sub-harmonic vibration, impeller retorqued'),
    ('FI-014', 'A-016', 'MISALIGNMENT',    '2026-07-20 09:30:00', 'Belt drive misalignment on blower',                          'MEDIUM',   4,   'BLWR 731 B - Axial dominant vibration, belt realigned'),
    ('FI-015', 'A-002', 'LUBRICATION',     '2026-08-10 07:00:00', 'Bearing grease breakdown under high temp operation',         'LOW',      2,   'COMP 510 A - Slow temperature rise, relubricated'),
    ('FI-016', 'A-009', 'BEARING_DEFECT',  '2026-08-28 16:45:00', 'DE bearing inner race defect on MTR 520 B',                 'CRITICAL', 36,  'MTR 520 B - Catastrophic failure, unplanned shutdown, motor replaced'),
    ('FI-017', 'A-024', 'ELECTRICAL',      '2026-09-05 11:00:00', 'Insulation degradation in process pump motor',               'HIGH',     16,  'PUMP 410 A - Electrical signature abnormal, motor rewound'),

    -- PLT-002 incidents (air compressors, extruders, fans)
    ('FI-018', 'A-028', 'BEARING_DEFECT',  '2025-10-20 09:00:00', 'Roller defect in compressor bearing',                       'HIGH',     15,  'COMP 610 A - Acceleration spike at BPFI, bearing replaced'),
    ('FI-019', 'A-037', 'MISALIGNMENT',    '2025-11-15 13:30:00', 'Gearbox-to-extruder misalignment',                          'MEDIUM',   8,   'MTR 710 A - 2x RPM elevated, precision alignment performed'),
    ('FI-020', 'A-040', 'UNBALANCE',       '2025-12-10 08:15:00', 'Blade pitch imbalance on cooling tower fan',                'MEDIUM',   4,   'FAN 810 A - 1x RPM dominant, blades rebalanced'),
    ('FI-021', 'A-033', 'LOOSENESS',       '2026-01-05 15:00:00', 'Bearing housing looseness on MTR 620 A',                    'MEDIUM',   5,   'MTR 620 A - Multiple harmonics, housing rebored and shimmed'),
    ('FI-022', 'A-030', 'LUBRICATION',     '2026-02-12 07:30:00', 'Grease starvation in COMP 610 B NDE bearing',               'LOW',      2,   'COMP 610 B - Temperature trending up, grease replenished'),
    ('FI-023', 'A-035', 'ELECTRICAL',      '2026-03-08 10:45:00', 'Stator winding fault in MTR 620 B',                         'HIGH',     20,  'MTR 620 B - 2x line freq + harmonics, motor replaced'),
    ('FI-024', 'A-044', 'BEARING_DEFECT',  '2026-04-15 14:00:00', 'Outer race pitting on FAN 810 C DE bearing',                'HIGH',     12,  'FAN 810 C - BPFO visible, bearing replaced during planned shutdown'),
    ('FI-025', 'A-038', 'UNBALANCE',       '2026-05-20 09:30:00', 'Screw wear causing mass imbalance on extruder',             'MEDIUM',   6,   'MTR 710 B - 1x radial dominant, screw rebalanced'),
    ('FI-026', 'A-028', 'MISALIGNMENT',    '2026-06-10 11:15:00', 'Soft foot condition after compressor overhaul',              'MEDIUM',   4,   'COMP 610 A - Axial vibration up, corrected soft foot'),
    ('FI-027', 'A-042', 'BEARING_DEFECT',  '2026-07-05 08:00:00', 'Inner race spalling on FAN 810 B NDE',                      'HIGH',     10,  'FAN 810 B - BPFI + sidebands, bearing replaced'),
    ('FI-028', 'A-048', 'LOOSENESS',       '2026-07-25 16:30:00', 'Conveyor motor mounting bolts worked loose',                'LOW',      2,   'MTR 910 B - Subsynchronous vibration, bolts retorqued'),
    ('FI-029', 'A-034', 'BEARING_DEFECT',  '2026-08-15 10:00:00', 'Cage defect in COMP 620 A DE bearing',                      'HIGH',     18,  'COMP 620 A - Acceleration trend + cage frequency, bearing replaced'),
    ('FI-030', 'A-046', 'LUBRICATION',     '2026-09-01 07:45:00', 'Grease contamination on FAN 810 D',                         'LOW',      2,   'FAN 810 D - Temperature uptrend, cleaned and regreased'),

    -- PLT-003 incidents (blowers, vacuum pumps, CW pumps, agitators)
    ('FI-031', 'A-054', 'BEARING_DEFECT',  '2025-11-08 09:30:00', 'Outer race defect on vacuum pump DE bearing',               'HIGH',     14,  'PUMP 230 A - BPFO peaks in acceleration, bearing replaced'),
    ('FI-032', 'A-050', 'MISALIGNMENT',    '2025-12-20 14:00:00', 'Motor-to-blower coupling misalignment',                     'MEDIUM',   5,   'BLWR 130 A - 2x RPM elevated, laser aligned'),
    ('FI-033', 'A-059', 'ELECTRICAL',      '2026-01-18 08:45:00', 'Partial discharge in CW pump motor winding',                'HIGH',     22,  'MTR 330 A - Electrical frequencies visible, motor rewound'),
    ('FI-034', 'A-063', 'UNBALANCE',       '2026-02-10 11:00:00', 'Agitator blade erosion causing imbalance',                  'MEDIUM',   6,   'MTR 430 A - 1x radial dominant, blades replaced and balanced'),
    ('FI-035', 'A-067', 'BEARING_DEFECT',  '2026-03-15 15:30:00', 'Ball defect in WTP blower NDE bearing',                     'MEDIUM',   8,   'BLWR 530 A - Acceleration increase, bearing replaced'),
    ('FI-036', 'A-056', 'LOOSENESS',       '2026-04-02 10:15:00', 'Pump coupling guard loose causing structural resonance',     'LOW',      2,   'PUMP 230 B - Half-order harmonics, guard tightened'),
    ('FI-037', 'A-052', 'LUBRICATION',     '2026-05-12 07:00:00', 'Grease hardening in AHU blower bearing',                    'LOW',      3,   'BLWR 130 B - Temperature increase, replaced grease'),
    ('FI-038', 'A-060', 'BEARING_DEFECT',  '2026-05-28 13:30:00', 'CW pump NDE bearing fatigue failure',                       'HIGH',     16,  'PUMP 330 A - Severe vibration, emergency bearing replacement'),
    ('FI-039', 'A-064', 'MISALIGNMENT',    '2026-06-22 09:00:00', 'Agitator shaft misalignment after gland repacking',         'MEDIUM',   4,   'MTR 430 B - Axial dominant, realigned'),
    ('FI-040', 'A-058', 'UNBALANCE',       '2026-07-10 14:45:00', 'Vacuum pump impeller deposit buildup',                      'MEDIUM',   5,   'PUMP 230 C - 1x radial, impeller cleaned and balanced'),
    ('FI-041', 'A-069', 'ELECTRICAL',      '2026-08-05 08:30:00', 'Rotor bar defect in WTP blower motor',                      'MEDIUM',   10,  'BLWR 530 B - Electrical signature anomaly, motor replaced'),
    ('FI-042', 'A-054', 'LUBRICATION',     '2026-08-20 16:00:00', 'Oil seal leak causing bearing lubrication loss',             'MEDIUM',   6,   'PUMP 230 A - Temperature alarm, seal and oil replaced'),
    ('FI-043', 'A-065', 'BEARING_DEFECT',  '2026-09-08 10:30:00', 'Inner race defect on reactor agitator motor',               'HIGH',     12,  'MTR 430 C - BPFI + modulation sidebands, bearing replaced');

-- ============================================================================
-- 2.10 SENSOR_READINGS (~1.2M rows, 12 months, hourly for 138 sensors)
--      With failure-mode-specific degradation patterns injected
-- ============================================================================
CREATE OR REPLACE TABLE SENSOR_READINGS (
    READING_ID      VARCHAR(30)   NOT NULL,
    SENSOR_ID       VARCHAR(20)   NOT NULL,
    READING_TS      TIMESTAMP_NTZ NOT NULL,
    X_VEL_RMS       FLOAT,        -- X-axis RMS Velocity (mm/sec)
    Y_VEL_RMS       FLOAT,        -- Y-axis RMS Velocity (mm/sec)
    Z_VEL_RMS       FLOAT,        -- Z-axis RMS Velocity (mm/sec)
    X_ACCEL_RMS     FLOAT,        -- X-axis RMS Acceleration (m/s²)
    Y_ACCEL_RMS     FLOAT,        -- Y-axis RMS Acceleration (m/s²)
    Z_ACCEL_RMS     FLOAT,        -- Z-axis RMS Acceleration (m/s²)
    TEMPERATURE_C   FLOAT,        -- Temperature (°C)
    PRIMARY KEY (READING_ID)
);

-- Generate sensor readings using Snowflake GENERATOR + failure degradation injection
-- Strategy:
--   1. Generate hourly timestamps for 12 months (Sep 2025 - Sep 2026)
--   2. Cross-join with all sensors to get base readings
--   3. Apply baseline vibration per asset type
--   4. Inject degradation ramps before each failure incident
--   5. Add realistic noise

-- Step 1: Create a mapping of which sensors are affected by which failures
CREATE OR REPLACE TEMPORARY TABLE FAILURE_SENSOR_MAP AS
SELECT
    fi.INCIDENT_ID,
    fi.ASSET_ID,
    fi.FAILURE_MODE,
    fi.FAILURE_TIMESTAMP,
    fi.SEVERITY,
    s.SENSOR_ID,
    s.MOUNT_POSITION,
    -- Degradation window: ramp starts 14-28 days before failure
    DATEADD('day', 
        CASE fi.SEVERITY 
            WHEN 'LOW' THEN -7 
            WHEN 'MEDIUM' THEN -14 
            WHEN 'HIGH' THEN -21 
            WHEN 'CRITICAL' THEN -28 
        END, 
        fi.FAILURE_TIMESTAMP) AS DEGRAD_START,
    fi.FAILURE_TIMESTAMP AS DEGRAD_END
FROM FAILURE_INCIDENTS fi
JOIN SENSORS s ON s.ASSET_ID = fi.ASSET_ID;

-- Step 2: Generate the actual readings
-- This is a large insert, using Snowflake's GENERATOR for the time dimension
INSERT INTO SENSOR_READINGS
WITH 
-- Generate hourly timestamps for 12 months (8760 hours)
time_spine AS (
    SELECT DATEADD('hour', SEQ4(), '2025-09-18 00:00:00'::TIMESTAMP_NTZ) AS ts
    FROM TABLE(GENERATOR(ROWCOUNT => 8784))  -- 366 days × 24 hours
    WHERE DATEADD('hour', SEQ4(), '2025-09-18 00:00:00'::TIMESTAMP_NTZ) <= '2026-09-18 23:00:00'::TIMESTAMP_NTZ
),
-- Cross join sensors × time, adding asset context
sensor_time AS (
    SELECT 
        s.SENSOR_ID,
        s.ASSET_ID,
        s.MOUNT_POSITION,
        t.ts AS READING_TS,
        a.ASSET_TYPE,
        a.MACHINE_CLASS,
        a.RATED_RPM,
        -- Base vibration levels by asset type (healthy machine)
        CASE a.ASSET_TYPE
            WHEN 'MOTOR'      THEN 0.5
            WHEN 'COMPRESSOR' THEN 0.8
            WHEN 'BLOWER'     THEN 0.6
            WHEN 'PUMP'       THEN 0.7
            WHEN 'FAN'        THEN 0.4
        END AS BASE_VEL,
        CASE a.ASSET_TYPE
            WHEN 'MOTOR'      THEN 1.0
            WHEN 'COMPRESSOR' THEN 1.5
            WHEN 'BLOWER'     THEN 1.2
            WHEN 'PUMP'       THEN 1.3
            WHEN 'FAN'        THEN 0.8
        END AS BASE_ACCEL,
        CASE a.ASSET_TYPE
            WHEN 'MOTOR'      THEN 38
            WHEN 'COMPRESSOR' THEN 42
            WHEN 'BLOWER'     THEN 35
            WHEN 'PUMP'       THEN 40
            WHEN 'FAN'        THEN 30
        END AS BASE_TEMP
    FROM SENSORS s
    JOIN ASSETS a ON a.ASSET_ID = s.ASSET_ID
    CROSS JOIN time_spine t
),
-- Calculate degradation multiplier for each sensor-timestamp pair
degradation AS (
    SELECT 
        st.*,
        -- Aggregate max degradation from all applicable failures
        COALESCE(MAX(
            CASE 
                WHEN st.READING_TS BETWEEN fsm.DEGRAD_START AND fsm.DEGRAD_END THEN
                    -- Progressive ramp: 1.0 at start → peak at failure time
                    -- Different failure modes affect different axes differently
                    TIMESTAMPDIFF('hour', fsm.DEGRAD_START, st.READING_TS)::FLOAT /
                    NULLIF(TIMESTAMPDIFF('hour', fsm.DEGRAD_START, fsm.DEGRAD_END), 0)::FLOAT
                WHEN st.READING_TS > fsm.DEGRAD_END AND st.READING_TS < DATEADD('day', 2, fsm.DEGRAD_END) THEN
                    -- Post-failure spike for 2 days, then repair
                    1.0 - (TIMESTAMPDIFF('hour', fsm.DEGRAD_END, st.READING_TS)::FLOAT / 48.0)
                ELSE 0
            END
        ), 0) AS DEGRAD_FACTOR,
        -- Track the dominant failure mode for axis weighting
        MAX(CASE 
            WHEN st.READING_TS BETWEEN fsm.DEGRAD_START AND fsm.DEGRAD_END THEN fsm.FAILURE_MODE
            ELSE NULL
        END) AS ACTIVE_FAILURE_MODE
    FROM sensor_time st
    LEFT JOIN FAILURE_SENSOR_MAP fsm 
        ON st.SENSOR_ID = fsm.SENSOR_ID
    GROUP BY st.SENSOR_ID, st.ASSET_ID, st.MOUNT_POSITION, st.READING_TS,
             st.ASSET_TYPE, st.MACHINE_CLASS, st.RATED_RPM,
             st.BASE_VEL, st.BASE_ACCEL, st.BASE_TEMP
)
SELECT
    -- Reading ID: sensor + timestamp hash
    SENSOR_ID || '-' || TO_CHAR(READING_TS, 'YYYYMMDDHH24') AS READING_ID,
    SENSOR_ID,
    READING_TS,
    
    -- X-axis velocity: base + degradation + noise
    GREATEST(0.01, ROUND(
        BASE_VEL * (1 + DEGRAD_FACTOR * 
            CASE ACTIVE_FAILURE_MODE
                WHEN 'UNBALANCE'       THEN 4.0   -- 1x RPM, strong radial
                WHEN 'MISALIGNMENT'    THEN 2.5   -- 2x RPM
                WHEN 'BEARING_DEFECT'  THEN 1.5   -- moderate velocity impact
                WHEN 'LOOSENESS'       THEN 3.0   -- multiple harmonics
                WHEN 'ELECTRICAL'      THEN 1.2   -- electrical frequencies
                WHEN 'LUBRICATION'     THEN 0.8   -- mild velocity increase
                ELSE 0
            END)
        + (RANDOM() / 9223372036854775807::FLOAT) * BASE_VEL * 0.15  -- 15% noise
        + SIN(EXTRACT(HOUR FROM READING_TS)::FLOAT * 0.26) * BASE_VEL * 0.05  -- diurnal pattern
    , 2)) AS X_VEL_RMS,
    
    -- Y-axis velocity
    GREATEST(0.01, ROUND(
        BASE_VEL * 0.9 * (1 + DEGRAD_FACTOR * 
            CASE ACTIVE_FAILURE_MODE
                WHEN 'UNBALANCE'       THEN 3.5
                WHEN 'MISALIGNMENT'    THEN 3.5   -- strong on coupling axis
                WHEN 'BEARING_DEFECT'  THEN 1.8
                WHEN 'LOOSENESS'       THEN 2.5
                WHEN 'ELECTRICAL'      THEN 1.0
                WHEN 'LUBRICATION'     THEN 0.6
                ELSE 0
            END)
        + (RANDOM() / 9223372036854775807::FLOAT) * BASE_VEL * 0.15
        + SIN(EXTRACT(HOUR FROM READING_TS)::FLOAT * 0.26 + 1.0) * BASE_VEL * 0.05
    , 2)) AS Y_VEL_RMS,
    
    -- Z-axis velocity (axial)
    GREATEST(0.01, ROUND(
        BASE_VEL * 0.7 * (1 + DEGRAD_FACTOR * 
            CASE ACTIVE_FAILURE_MODE
                WHEN 'UNBALANCE'       THEN 1.5   -- weak axial for unbalance
                WHEN 'MISALIGNMENT'    THEN 5.0   -- STRONG axial for misalignment
                WHEN 'BEARING_DEFECT'  THEN 2.0
                WHEN 'LOOSENESS'       THEN 2.0
                WHEN 'ELECTRICAL'      THEN 0.8
                WHEN 'LUBRICATION'     THEN 0.5
                ELSE 0
            END)
        + (RANDOM() / 9223372036854775807::FLOAT) * BASE_VEL * 0.12
        + SIN(EXTRACT(HOUR FROM READING_TS)::FLOAT * 0.26 + 2.0) * BASE_VEL * 0.04
    , 2)) AS Z_VEL_RMS,
    
    -- X-axis acceleration (high-frequency — bearing defects show here)
    GREATEST(0.05, ROUND(
        BASE_ACCEL * (1 + DEGRAD_FACTOR * 
            CASE ACTIVE_FAILURE_MODE
                WHEN 'BEARING_DEFECT'  THEN 8.0   -- DOMINANT in acceleration
                WHEN 'LUBRICATION'     THEN 4.0   -- shows in high freq
                WHEN 'LOOSENESS'       THEN 3.0
                WHEN 'UNBALANCE'       THEN 1.0   -- minimal accel impact
                WHEN 'MISALIGNMENT'    THEN 1.5
                WHEN 'ELECTRICAL'      THEN 2.0
                ELSE 0
            END)
        + (RANDOM() / 9223372036854775807::FLOAT) * BASE_ACCEL * 0.2
    , 2)) AS X_ACCEL_RMS,
    
    -- Y-axis acceleration
    GREATEST(0.05, ROUND(
        BASE_ACCEL * 0.95 * (1 + DEGRAD_FACTOR * 
            CASE ACTIVE_FAILURE_MODE
                WHEN 'BEARING_DEFECT'  THEN 7.0
                WHEN 'LUBRICATION'     THEN 3.5
                WHEN 'LOOSENESS'       THEN 2.5
                WHEN 'UNBALANCE'       THEN 0.8
                WHEN 'MISALIGNMENT'    THEN 1.2
                WHEN 'ELECTRICAL'      THEN 1.8
                ELSE 0
            END)
        + (RANDOM() / 9223372036854775807::FLOAT) * BASE_ACCEL * 0.2
    , 2)) AS Y_ACCEL_RMS,
    
    -- Z-axis acceleration
    GREATEST(0.05, ROUND(
        BASE_ACCEL * 0.85 * (1 + DEGRAD_FACTOR * 
            CASE ACTIVE_FAILURE_MODE
                WHEN 'BEARING_DEFECT'  THEN 6.0
                WHEN 'LUBRICATION'     THEN 3.0
                WHEN 'LOOSENESS'       THEN 2.0
                WHEN 'UNBALANCE'       THEN 0.6
                WHEN 'MISALIGNMENT'    THEN 2.5   -- axial accel for misalignment
                WHEN 'ELECTRICAL'      THEN 1.5
                ELSE 0
            END)
        + (RANDOM() / 9223372036854775807::FLOAT) * BASE_ACCEL * 0.18
    , 2)) AS Z_ACCEL_RMS,
    
    -- Temperature
    GREATEST(22, ROUND(
        BASE_TEMP 
        + DEGRAD_FACTOR * 
            CASE ACTIVE_FAILURE_MODE
                WHEN 'BEARING_DEFECT'  THEN 15   -- bearing heat
                WHEN 'LUBRICATION'     THEN 20   -- friction heat
                WHEN 'MISALIGNMENT'    THEN 8
                WHEN 'LOOSENESS'       THEN 5
                WHEN 'UNBALANCE'       THEN 3
                WHEN 'ELECTRICAL'      THEN 12   -- winding heat
                ELSE 0
            END
        + (RANDOM() / 9223372036854775807::FLOAT) * 4  -- noise
        + SIN(EXTRACT(HOUR FROM READING_TS)::FLOAT * 0.26) * 2  -- diurnal
        + CASE EXTRACT(MONTH FROM READING_TS)  -- seasonal
            WHEN 4 THEN 3 WHEN 5 THEN 5 WHEN 6 THEN 7
            WHEN 7 THEN 8 WHEN 8 THEN 6 WHEN 9 THEN 4
            ELSE 0
          END
    , 1)) AS TEMPERATURE_C

FROM degradation;

-- ============================================================================
-- 2.11 TICKETS (~100 maintenance tickets with full lifecycle)
-- ============================================================================
CREATE OR REPLACE TABLE TICKETS (
    TICKET_ID                   VARCHAR(30)   NOT NULL,
    ASSET_ID                    VARCHAR(20)   NOT NULL,
    INCIDENT_ID                 VARCHAR(20),          -- linked failure incident (if any)
    ISSUE_OPEN_DATE             TIMESTAMP_NTZ NOT NULL,
    SEVERITY                    VARCHAR(10)   NOT NULL, -- LOW, MEDIUM, HIGH, CRITICAL
    STATUS                      VARCHAR(15)   NOT NULL, -- OPEN, ACKNOWLEDGED, IN_PROGRESS, CLOSED
    ACKNOWLEDGED_BY             VARCHAR(20),
    ACKNOWLEDGE_DATE            TIMESTAMP_NTZ,
    ASSIGNED_TO                 VARCHAR(20),
    CORRECTIVE_ACTIONS_REC      VARCHAR(500),
    CORRECTIVE_ACTIONS_TAKEN    VARCHAR(500),
    ISSUE_CLOSURE_DATE          TIMESTAMP_NTZ,
    PRE_REPAIR_HEALTH_SCORE     INT,                   -- 0-100
    POST_REPAIR_HEALTH_SCORE    INT,                   -- 0-100
    OPENED_BY                   VARCHAR(20),
    CLOSED_BY                   VARCHAR(20),
    COMMENTS                    VARCHAR(1000),
    PRIMARY KEY (TICKET_ID)
);

-- Generate tickets from failure incidents + some proactive/routine tickets
INSERT INTO TICKETS
-- Tickets linked to failure incidents (closed)
SELECT
    'TK-' || LPAD(ROW_NUMBER() OVER (ORDER BY fi.FAILURE_TIMESTAMP)::VARCHAR, 4, '0') AS TICKET_ID,
    fi.ASSET_ID,
    fi.INCIDENT_ID,
    DATEADD('hour', -UNIFORM(2, 48, RANDOM()), fi.FAILURE_TIMESTAMP)  AS ISSUE_OPEN_DATE,
    fi.SEVERITY,
    'CLOSED'                                                          AS STATUS,
    -- Acknowledged by: vibration analyst of the corresponding plant
    (SELECT u.USER_ID FROM USERS u 
     JOIN ASSETS a ON TRUE 
     JOIN ASSET_GROUPS ag ON a.GROUP_ID = ag.GROUP_ID
     JOIN AREAS ar ON ag.AREA_ID = ar.AREA_ID
     WHERE a.ASSET_ID = fi.ASSET_ID AND u.PLANT_ID = ar.PLANT_ID AND u.ROLE = 'VIB_ANALYST'
     LIMIT 1)                                                         AS ACKNOWLEDGED_BY,
    DATEADD('hour', UNIFORM(1, 8, RANDOM()), 
        DATEADD('hour', -UNIFORM(2, 48, RANDOM()), fi.FAILURE_TIMESTAMP)) AS ACKNOWLEDGE_DATE,
    (SELECT u.USER_ID FROM USERS u 
     JOIN ASSETS a ON TRUE 
     JOIN ASSET_GROUPS ag ON a.GROUP_ID = ag.GROUP_ID
     JOIN AREAS ar ON ag.AREA_ID = ar.AREA_ID
     WHERE a.ASSET_ID = fi.ASSET_ID AND u.PLANT_ID = ar.PLANT_ID AND u.ROLE = 'MAINT_ENGINEER'
     LIMIT 1)                                                         AS ASSIGNED_TO,
    CASE fi.FAILURE_MODE
        WHEN 'BEARING_DEFECT'  THEN 'Bearing Replacement, Vibration Monitoring'
        WHEN 'MISALIGNMENT'    THEN 'Laser Alignment, Coupling Inspection'
        WHEN 'UNBALANCE'       THEN 'Dynamic Balancing, Deposit Cleaning'
        WHEN 'LOOSENESS'       THEN 'Bolt Retorquing, Foundation Inspection'
        WHEN 'ELECTRICAL'      THEN 'Motor Rewinding, Insulation Testing'
        WHEN 'LUBRICATION'     THEN 'Relubrication, Oil Analysis, Seal Inspection'
    END                                                               AS CORRECTIVE_ACTIONS_REC,
    fi.DESCRIPTION                                                    AS CORRECTIVE_ACTIONS_TAKEN,
    DATEADD('hour', fi.DOWNTIME_HOURS::INT + UNIFORM(2, 12, RANDOM()), fi.FAILURE_TIMESTAMP) AS ISSUE_CLOSURE_DATE,
    UNIFORM(15, 55, RANDOM())                                         AS PRE_REPAIR_HEALTH_SCORE,
    UNIFORM(78, 98, RANDOM())                                         AS POST_REPAIR_HEALTH_SCORE,
    'USR-013'                                                         AS OPENED_BY,   -- MachPulse system
    (SELECT u.USER_ID FROM USERS u 
     JOIN ASSETS a ON TRUE 
     JOIN ASSET_GROUPS ag ON a.GROUP_ID = ag.GROUP_ID
     JOIN AREAS ar ON ag.AREA_ID = ar.AREA_ID
     WHERE a.ASSET_ID = fi.ASSET_ID AND u.PLANT_ID = ar.PLANT_ID AND u.ROLE = 'MAINT_ENGINEER'
     LIMIT 1)                                                         AS CLOSED_BY,
    'Auto-generated from vibration alert. ' || fi.DESCRIPTION         AS COMMENTS
FROM FAILURE_INCIDENTS fi;

-- Add some currently OPEN tickets (recent alerts not yet resolved)
INSERT INTO TICKETS VALUES
    ('TK-0044', 'A-010', NULL, '2026-09-12 08:30:00', 'MEDIUM', 'OPEN',        NULL,      NULL,                        NULL,      'Vibration trending up on COMP 520 B, monitor closely', NULL, NULL, 48, NULL, 'USR-013', NULL, 'Velocity trending from 1.2 to 1.8 mm/s over 2 weeks'),
    ('TK-0045', 'A-029', NULL, '2026-09-14 10:15:00', 'LOW',    'ACKNOWLEDGED', 'USR-007', '2026-09-14 11:00:00',       'USR-006', 'Schedule lubrication check on COMP 610 B', NULL, NULL, 62, NULL, 'USR-013', NULL, 'Temperature trending 3°C above baseline'),
    ('TK-0046', 'A-059', NULL, '2026-09-15 14:45:00', 'HIGH',   'IN_PROGRESS',  'USR-011', '2026-09-15 15:30:00',       'USR-010', 'Bearing Replacement, Alignment Check on MTR 330 A', NULL, NULL, 32, NULL, 'USR-013', NULL, 'Acceleration spike detected, bearing defect frequency visible'),
    ('TK-0047', 'A-040', NULL, '2026-09-16 07:00:00', 'MEDIUM', 'OPEN',        NULL,      NULL,                        NULL,      'Balance check required on FAN 810 A', NULL, NULL, 55, NULL, 'USR-007', NULL, '1x RPM velocity increased by 40% since last month'),
    ('TK-0048', 'A-063', NULL, '2026-09-17 09:30:00', 'HIGH',   'ACKNOWLEDGED', 'USR-011', '2026-09-17 10:15:00',       'USR-010', 'Bearing inspection, check for looseness on MTR 430 A', NULL, NULL, 38, NULL, 'USR-013', NULL, 'Multiple harmonics visible, potential looseness developing');

-- ============================================================================
-- 2.12 ERP_PRODUCTION_RUNS (~6K rows for OEE calculation)
-- ============================================================================
CREATE OR REPLACE TABLE ERP_PRODUCTION_RUNS (
    RUN_ID              VARCHAR(20)   NOT NULL,
    PLANT_ID            VARCHAR(20)   NOT NULL,
    PRODUCTION_LINE     VARCHAR(50)   NOT NULL,
    SHIFT               VARCHAR(10)   NOT NULL,   -- DAY, EVENING, NIGHT
    RUN_DATE            DATE          NOT NULL,
    PLANNED_RUNTIME_MIN FLOAT         NOT NULL,
    ACTUAL_RUNTIME_MIN  FLOAT         NOT NULL,
    PLANNED_DOWNTIME_MIN FLOAT        DEFAULT 0,
    UNPLANNED_DOWNTIME_MIN FLOAT      DEFAULT 0,
    PLANNED_QUANTITY    INT           NOT NULL,
    ACTUAL_QUANTITY     INT           NOT NULL,
    GOOD_QUANTITY       INT           NOT NULL,
    IDEAL_CYCLE_TIME_SEC FLOAT,
    PRODUCT_CODE        VARCHAR(20),
    PRIMARY KEY (RUN_ID)
);

-- Generate 12 months of production data for 3 plants × 3 lines × 3 shifts
INSERT INTO ERP_PRODUCTION_RUNS
WITH 
date_spine AS (
    SELECT DATEADD('day', SEQ4(), '2025-09-18')::DATE AS run_date
    FROM TABLE(GENERATOR(ROWCOUNT => 366))
    WHERE DATEADD('day', SEQ4(), '2025-09-18')::DATE <= '2026-09-18'
),
plants AS (
    SELECT * FROM (VALUES 
        ('PLT-001', 'Reactor Line A',   'CHEM-A'),
        ('PLT-001', 'Reactor Line B',   'CHEM-B'),
        ('PLT-001', 'Distillation Line','CHEM-C'),
        ('PLT-002', 'Extrusion Line 1', 'POLY-A'),
        ('PLT-002', 'Extrusion Line 2', 'POLY-B'),
        ('PLT-002', 'Moulding Line',    'POLY-C'),
        ('PLT-003', 'API Synthesis',    'PHRM-A'),
        ('PLT-003', 'Formulation Line', 'PHRM-B'),
        ('PLT-003', 'Packaging Line',   'PHRM-C')
    ) AS t(plant_id, line_name, product_code)
),
shifts AS (
    SELECT * FROM (VALUES ('DAY'), ('EVENING'), ('NIGHT')) AS t(shift)
),
base AS (
    SELECT 
        'RUN-' || LPAD(ROW_NUMBER() OVER (ORDER BY d.run_date, p.plant_id, p.line_name, s.shift)::VARCHAR, 6, '0') AS run_id,
        p.plant_id,
        p.line_name AS production_line,
        s.shift,
        d.run_date,
        480.0 AS planned_runtime_min,  -- 8-hour shifts
        30.0  AS planned_downtime_min, -- 30 min planned maintenance per shift
        p.product_code,
        -- Inject unplanned downtime during failure windows
        CASE 
            WHEN EXISTS (
                SELECT 1 FROM FAILURE_INCIDENTS fi
                JOIN ASSETS a ON fi.ASSET_ID = a.ASSET_ID
                JOIN ASSET_GROUPS ag ON a.GROUP_ID = ag.GROUP_ID
                JOIN AREAS ar ON ag.AREA_ID = ar.AREA_ID
                WHERE ar.PLANT_ID = p.plant_id
                AND d.run_date BETWEEN fi.FAILURE_TIMESTAMP::DATE AND DATEADD('day', CEIL(fi.DOWNTIME_HOURS/24), fi.FAILURE_TIMESTAMP)::DATE
            ) THEN UNIFORM(30, 180, RANDOM())::FLOAT
            ELSE UNIFORM(0, 15, RANDOM())::FLOAT  -- normal minor stoppages
        END AS unplanned_dt
    FROM date_spine d
    CROSS JOIN plants p
    CROSS JOIN shifts s
)
SELECT
    run_id,
    plant_id,
    production_line,
    shift,
    run_date,
    planned_runtime_min,
    GREATEST(60, planned_runtime_min - planned_downtime_min - unplanned_dt + UNIFORM(-10, 10, RANDOM())) AS actual_runtime_min,
    planned_downtime_min,
    unplanned_dt AS unplanned_downtime_min,
    UNIFORM(800, 1200, RANDOM()) AS planned_quantity,
    GREATEST(100, UNIFORM(700, 1150, RANDOM()) - CASE WHEN unplanned_dt > 60 THEN UNIFORM(100, 300, RANDOM()) ELSE 0 END) AS actual_quantity,
    GREATEST(80, UNIFORM(680, 1130, RANDOM()) - CASE WHEN unplanned_dt > 60 THEN UNIFORM(120, 320, RANDOM()) ELSE 0 END) AS good_quantity,
    UNIFORM(15, 45, RANDOM())::FLOAT AS ideal_cycle_time_sec,
    product_code
FROM base;

-- ============================================================================
-- Verification counts
-- ============================================================================
SELECT 'PLANTS' AS TBL, COUNT(*) AS ROW_CNT FROM PLANTS
UNION ALL SELECT 'AREAS', COUNT(*) FROM AREAS
UNION ALL SELECT 'ASSET_GROUPS', COUNT(*) FROM ASSET_GROUPS
UNION ALL SELECT 'ASSETS', COUNT(*) FROM ASSETS
UNION ALL SELECT 'SENSORS', COUNT(*) FROM SENSORS
UNION ALL SELECT 'ISO_THRESHOLDS', COUNT(*) FROM ISO_THRESHOLDS
UNION ALL SELECT 'USERS', COUNT(*) FROM USERS
UNION ALL SELECT 'NOTIFICATION_RULES', COUNT(*) FROM NOTIFICATION_RULES
UNION ALL SELECT 'FAILURE_INCIDENTS', COUNT(*) FROM FAILURE_INCIDENTS
UNION ALL SELECT 'SENSOR_READINGS', COUNT(*) FROM SENSOR_READINGS
UNION ALL SELECT 'TICKETS', COUNT(*) FROM TICKETS
UNION ALL SELECT 'ERP_PRODUCTION_RUNS', COUNT(*) FROM ERP_PRODUCTION_RUNS
ORDER BY 1;
