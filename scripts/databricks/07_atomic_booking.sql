-- atomic_booking: 5-table ledger for atomic 4-way booking (bed + ambulance + doctor + drug)
--
-- design:
--   transactions = master ledger (transaction_id PK, status RESERVED→COMMITTED→ROLLED_BACK)
--   4 resource tables (bed/ambulance/doctor/drug) all carry transaction_id
--   a successful booking writes 1 row to transactions then 1 row to each of the 4 resource tables
--   on any failure: UPDATE transactions.status='ROLLED_BACK', resource rows are filtered out by joining on transactions.status='COMMITTED'
--
-- this is a saga-style pattern, not real cross-table ACID — but it gives the same UX guarantees for the demo,
-- and Delta gives us per-table ACID for the writes themselves. all 5 tables have CDF on for downstream observability.

CREATE OR REPLACE TABLE workspace.default.txn_atomic (
  transaction_id    STRING NOT NULL,
  patient_id        STRING,
  facility_id       STRING,
  status            STRING,                -- RESERVED | COMMITTED | ROLLED_BACK | EXPIRED
  failure_reason    STRING,
  created_ts        TIMESTAMP,
  updated_ts        TIMESTAMP,
  CONSTRAINT txn_pk PRIMARY KEY (transaction_id)
) TBLPROPERTIES (delta.enableChangeDataFeed = true);

CREATE OR REPLACE TABLE workspace.default.bed_reservations (
  reservation_id    STRING NOT NULL,
  transaction_id    STRING NOT NULL,
  facility_id       STRING NOT NULL,
  bed_id            STRING,                -- e.g. "ICU-3", "Ward-A-12"
  bed_type          STRING,                -- icu | ward | private | general
  patient_id        STRING,
  start_ts          TIMESTAMP,
  end_ts            TIMESTAMP,
  status            STRING,                -- RESERVED | CONFIRMED | CHECKED_IN | RELEASED | CANCELLED
  created_ts        TIMESTAMP,
  updated_ts        TIMESTAMP,
  CONSTRAINT bed_pk PRIMARY KEY (reservation_id)
) TBLPROPERTIES (delta.enableChangeDataFeed = true);

CREATE OR REPLACE TABLE workspace.default.ambulance_dispatches (
  dispatch_id       STRING NOT NULL,
  transaction_id    STRING NOT NULL,
  facility_id       STRING NOT NULL,
  ambulance_id      STRING,                -- vehicle ref
  patient_id        STRING,
  pickup_lat        DOUBLE,
  pickup_lon        DOUBLE,
  dropoff_lat       DOUBLE,
  dropoff_lon       DOUBLE,
  pickup_ts         TIMESTAMP,
  eta_ts            TIMESTAMP,
  status            STRING,                -- DISPATCHED | EN_ROUTE | ARRIVED | COMPLETED | CANCELLED
  created_ts        TIMESTAMP,
  updated_ts        TIMESTAMP,
  CONSTRAINT amb_pk PRIMARY KEY (dispatch_id)
) TBLPROPERTIES (delta.enableChangeDataFeed = true);

CREATE OR REPLACE TABLE workspace.default.doctor_slots (
  slot_id           STRING NOT NULL,
  transaction_id    STRING NOT NULL,
  facility_id       STRING NOT NULL,
  doctor_id         STRING,                -- doctor ref (string for now, no doctor table yet)
  specialty         STRING,
  patient_id        STRING,
  slot_start        TIMESTAMP,
  slot_end          TIMESTAMP,
  status            STRING,                -- RESERVED | CONFIRMED | IN_PROGRESS | COMPLETED | NO_SHOW | CANCELLED
  created_ts        TIMESTAMP,
  updated_ts        TIMESTAMP,
  CONSTRAINT doc_pk PRIMARY KEY (slot_id)
) TBLPROPERTIES (delta.enableChangeDataFeed = true);

CREATE OR REPLACE TABLE workspace.default.drug_reservations (
  reservation_id    STRING NOT NULL,
  transaction_id    STRING NOT NULL,
  facility_id       STRING NOT NULL,
  drug_code         STRING,                -- WHO ATC code or local SKU
  drug_name         STRING,
  quantity          DOUBLE,
  unit              STRING,                -- mg | ml | tab | vial
  patient_id        STRING,
  status            STRING,                -- RESERVED | DISPENSED | RETURNED | CANCELLED
  created_ts        TIMESTAMP,
  updated_ts        TIMESTAMP,
  CONSTRAINT drug_pk PRIMARY KEY (reservation_id)
) TBLPROPERTIES (delta.enableChangeDataFeed = true);

-- view: only resources that belong to a COMMITTED transaction count as "really booked"
CREATE OR REPLACE VIEW workspace.default.v_committed_bookings AS
SELECT
  t.transaction_id, t.patient_id, t.facility_id, t.created_ts AS booked_at,
  b.reservation_id AS bed_reservation_id, b.bed_id, b.bed_type, b.start_ts AS bed_start, b.end_ts AS bed_end,
  a.dispatch_id, a.ambulance_id, a.pickup_ts AS ambulance_pickup, a.eta_ts AS ambulance_eta,
  d.slot_id AS doctor_slot_id, d.doctor_id, d.specialty AS doctor_specialty, d.slot_start AS doctor_start,
  r.reservation_id AS drug_reservation_id, r.drug_name, r.quantity AS drug_qty, r.unit AS drug_unit
FROM workspace.default.txn_atomic t
LEFT JOIN workspace.default.bed_reservations    b ON t.transaction_id = b.transaction_id
LEFT JOIN workspace.default.ambulance_dispatches a ON t.transaction_id = a.transaction_id
LEFT JOIN workspace.default.doctor_slots        d ON t.transaction_id = d.transaction_id
LEFT JOIN workspace.default.drug_reservations   r ON t.transaction_id = r.transaction_id
WHERE t.status = 'COMMITTED';
