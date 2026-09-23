-- PostgreSQL Seed Database Script for GenAI Data Assistant
-- Defines sample domain tables (customers, products, orders) supporting revenue analytics.

CREATE TABLE IF NOT EXISTS customers (
    customer_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    country VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    product_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    price NUMERIC(10, 2) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orders (
    order_id SERIAL PRIMARY KEY,
    customer_id INT REFERENCES customers(customer_id) ON DELETE CASCADE,
    product_id INT REFERENCES products(product_id) ON DELETE CASCADE,
    quantity INT NOT NULL DEFAULT 1,
    unit_price NUMERIC(10, 2) NOT NULL,
    total_amount NUMERIC(10, 2) NOT NULL,
    order_date DATE NOT NULL DEFAULT CURRENT_DATE,
    status VARCHAR(50) NOT NULL DEFAULT 'completed',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS documents (
    id VARCHAR(36) PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    file_path VARCHAR(512) NOT NULL,
    size BIGINT NOT NULL,
    pages INT NOT NULL DEFAULT 1,
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Seed Sample Records for Revenue and Analytics Queries
INSERT INTO customers (name, email, country) VALUES
('Acme Corp', 'contact@acme.com', 'United States'),
('Global Tech LLC', 'info@globaltech.io', 'Germany'),
('Nexus Systems', 'support@nexus.co', 'United Kingdom'),
('Aura Retail', 'sales@auraretail.com', 'Canada');

INSERT INTO products (name, category, price) VALUES
('Enterprise AI Assistant', 'Software', 4999.99),
('Data Analytics Dashboard', 'Software', 1999.50),
('Cloud Storage Package', 'Infrastructure', 499.00),
('24/7 Premium Support', 'Services', 1200.00);

INSERT INTO orders (customer_id, product_id, quantity, unit_price, total_amount, order_date, status) VALUES
(1, 1, 2, 4999.99, 9999.98, '2026-01-15', 'completed'),
(1, 4, 1, 1200.00, 1200.00, '2026-01-15', 'completed'),
(2, 2, 5, 1999.50, 9997.50, '2026-02-01', 'completed'),
(3, 3, 10, 499.00, 4990.00, '2026-02-20', 'completed'),
(4, 1, 1, 4999.99, 4999.99, '2026-03-05', 'completed'),
(2, 4, 2, 1200.00, 2400.00, '2026-03-10', 'completed');
