-- Example schema for the demo invoicing package. Not used by any real database.
CREATE TABLE invoices (
    id            BIGINT PRIMARY KEY,
    customer_ref  TEXT    NOT NULL,
    subtotal_minor BIGINT NOT NULL,
    tax_minor     BIGINT  NOT NULL,
    total_minor   BIGINT  NOT NULL,
    created_at    TIMESTAMP NOT NULL
);
