-- NERV Database Test: 1750 ODP Level 01 Residential Lobby
-- EVA-00 Schema INSERT statements for extracted data
-- Generated: 2026-02-18

-- Project
INSERT INTO projects (project_id, name, address, building_type, stories)
VALUES ('1750-ODP', '1750 ODP', '1750 Ocean Drive Place', 'residential_multifamily', 9);

-- Building Levels (from sheet names - elevations TBD)
INSERT INTO building_levels (project_id, level_code, level_name, sheet_ref, ff_elevation_ngvd, notes)
VALUES 
  ('1750-ODP', 'L01', 'Level 01', 'A-101', NULL, 'Ground level. FF elevation not on arch floor plans.'),
  ('1750-ODP', 'L02', 'Level 02', 'A-102', NULL, NULL),
  ('1750-ODP', 'L03', 'Level 03', 'A-103', NULL, NULL),
  ('1750-ODP', 'L04', 'Level 04', 'A-104', NULL, NULL),
  ('1750-ODP', 'L05', 'Level 05', 'A-105', NULL, NULL),
  ('1750-ODP', 'L06', 'Level 06', 'A-106', NULL, 'Typical floor (L06-07)'),
  ('1750-ODP', 'L07', 'Level 07', 'A-106', NULL, 'Typical floor (L06-07)'),
  ('1750-ODP', 'L08', 'Level 08', 'A-108', NULL, NULL),
  ('1750-ODP', 'L09', 'Level 09', 'A-109', NULL, 'Mech equip + roof');

-- Rooms (Level 01 - from A-101 extraction)
INSERT INTO rooms (project_id, level_code, room_id, room_name, room_type, x_coord, y_coord)
VALUES
  ('1750-ODP', 'L01', 'L01-024', 'RESIDENTIAL LOBBY', 'lobby', -225.0, -1721.8),
  ('1750-ODP', 'L01', 'L01-015', 'ELEV.', 'elevator', 68.0, -1721.8),
  ('1750-ODP', 'L01', 'L01-020', 'MOVE-IN ROOM', 'service', NULL, NULL),
  ('1750-ODP', 'L01', 'L01-088', 'TRASH', 'service', NULL, NULL);

-- Elevation data points (what we found)
INSERT INTO elevation_data (project_id, level_code, data_type, value, unit, source_sheet, source_layer, notes)
VALUES
  ('1750-ODP', 'L01', 'ramp_slope', 6.10, 'percent', 'A-101', 'G-ANNO-DIMS', 'Entry ramp slopes DN toward lobby'),
  ('1750-ODP', 'L01', 'direction', NULL, NULL, 'A-101', 'A-FLOR-LEVL-TEXT', 'DN indicator at (-345,-1499)'),
  ('1750-ODP', NULL, 'note', NULL, NULL, 'A-121', 'G-ANNO-TEXT', 'ALL ELEVATIONS ARE RELATIVE TO TOP OF SLAB ELEVATION OF [TRUNCATED]');

-- Data gaps
INSERT INTO data_gaps (project_id, gap_type, description, sheets_needed, priority)
VALUES
  ('1750-ODP', 'missing_elevation', 'FF/NGVD elevation for Level 01 (Residential Lobby L01-024)', 'A-200 series (sections), S-100 (structural), C-100 (civil)', 'HIGH'),
  ('1750-ODP', 'truncated_note', 'RCP note "ALL ELEVATIONS ARE RELATIVE TO TOP OF SLAB ELEVATION OF" is truncated - missing the actual elevation value', 'A-001 or G-001 (general notes)', 'MEDIUM'),
  ('1750-ODP', 'missing_sheets', 'Only arch floor plans (A-101 to A-109) and RCPs (A-121 to A-128) provided. No sections, elevations, structural, or civil sheets.', 'A-200, A-300, S-series, C-series', 'HIGH');
