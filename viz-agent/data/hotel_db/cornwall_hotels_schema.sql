-- Cornwall Hotels SQLite Schema and Data

CREATE TABLE IF NOT EXISTS hotels (
    hotel_id INTEGER PRIMARY KEY AUTOINCREMENT,
    hotel_name TEXT NOT NULL,
    town TEXT NOT NULL,
    address TEXT NOT NULL,
    rating REAL NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS hotel_room_offers (
    offer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    hotel_id INTEGER NOT NULL,
    available_rooms INTEGER NOT NULL,
    price_single REAL NOT NULL,
    price_double REAL NOT NULL,
    FOREIGN KEY (hotel_id) REFERENCES hotels(hotel_id)
);

CREATE TABLE IF NOT EXISTS hotel_performance_metrics (
    metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
    hotel_id INTEGER NOT NULL UNIQUE,
    market_segment TEXT NOT NULL,
    star_category TEXT NOT NULL,
    peak_season TEXT NOT NULL,
    occupancy_rate REAL NOT NULL,
    cancellation_rate REAL NOT NULL,
    avg_length_of_stay REAL NOT NULL,
    monthly_revenue REAL NOT NULL,
    review_count INTEGER NOT NULL,
    repeat_guest_rate REAL NOT NULL,
    distance_beach_km REAL NOT NULL,
    distance_station_km REAL NOT NULL,
    family_score REAL NOT NULL,
    business_score REAL NOT NULL,
    sustainability_score REAL NOT NULL,
    spa_available INTEGER NOT NULL,
    pet_friendly INTEGER NOT NULL,
    parking_spaces INTEGER NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    FOREIGN KEY (hotel_id) REFERENCES hotels(hotel_id)
);

-- Pre-populate hotels
INSERT INTO hotels (hotel_name, town, address, rating, description) VALUES
('Seaview Hotel', 'Newquay', '1 Beach Rd, Newquay', 4.5, 'A beautiful hotel overlooking the sea.'),
('Harbour Inn', 'Falmouth', '12 Harbour St, Falmouth', 4.2, 'Charming inn near the harbour.'),
('Cornish Retreat', 'St Austell', '5 Retreat Ln, St Austell', 4.0, 'Relaxing retreat in the heart of Cornwall.'),
('Penzance Palace', 'Penzance', '22 Promenade, Penzance', 4.7, 'Luxury hotel with sea views.'),
('The Camborne Arms', 'Camborne', '8 Main St, Camborne', 4.1, 'Friendly hotel in Camborne.'),
('Hayle Haven', 'Hayle', '3 River Rd, Hayle', 4.3, 'Comfortable stay near the river.'),
('Land''s End Lodge', 'Land''s End', 'Land''s End Rd, Land''s End', 4.6, 'Stay at the edge of England.'),
('Bude Beach Hotel', 'Bude', '7 Beach Parade, Bude', 4.4, 'Steps from the sand.'),
('Padstow Quay Inn', 'Padstow', '2 Quay St, Padstow', 4.5, 'Quayside inn with great food.'),
('St Ives Bay Resort', 'St Ives', '9 Bay Rd, St Ives', 4.8, 'Resort with stunning bay views.');

-- Pre-populate hotel room offers
INSERT INTO hotel_room_offers (hotel_id, available_rooms, price_single, price_double) VALUES
(1, 5, 120.00, 180.00),
(2, 2, 95.00, 150.00),
(3, 8, 110.00, 170.00),
(4, 3, 130.00, 200.00),
(5, 4, 105.00, 160.00),
(6, 6, 99.00, 145.00),
(7, 2, 150.00, 220.00),
(8, 7, 115.00, 175.00),
(9, 5, 125.00, 185.00),
(10, 6, 140.00, 210.00); 

-- Enriched one-row-per-hotel analytics for richer charting examples
INSERT INTO hotel_performance_metrics (
    hotel_id, market_segment, star_category, peak_season,
    occupancy_rate, cancellation_rate, avg_length_of_stay, monthly_revenue,
    review_count, repeat_guest_rate, distance_beach_km, distance_station_km,
    family_score, business_score, sustainability_score,
    spa_available, pet_friendly, parking_spaces, latitude, longitude
) VALUES
(1,  'Leisure',   'Upscale',   'Summer', 0.87, 0.08, 3.2, 142000.00, 1240, 0.31, 0.2, 1.8, 4.6, 3.8, 4.1, 1, 1, 42, 50.4155, -5.0737),
(2,  'Leisure',   'Boutique',  'Summer', 0.76, 0.11, 2.6,  68000.00,  720, 0.24, 0.4, 0.7, 4.2, 4.1, 3.8, 0, 1, 18, 50.1526, -5.0657),
(3,  'Family',    'Midscale',  'Autumn', 0.69, 0.14, 2.9,  82000.00,  540, 0.28, 6.5, 1.2, 4.4, 3.5, 4.3, 1, 0, 55, 50.3382, -4.7950),
(4,  'Luxury',    'Luxury',    'Summer', 0.91, 0.06, 3.8, 188000.00, 1580, 0.37, 0.1, 0.9, 4.7, 4.2, 4.5, 1, 0, 36, 50.1188, -5.5376),
(5,  'Business',  'Midscale',  'Spring', 0.63, 0.17, 1.9,  61000.00,  390, 0.18, 7.8, 0.4, 3.6, 4.5, 3.9, 0, 1, 64, 50.2130, -5.2970),
(6,  'Family',    'Boutique',  'Summer', 0.82, 0.09, 3.1,  94000.00,  810, 0.33, 1.1, 0.8, 4.5, 3.6, 4.6, 0, 1, 24, 50.1855, -5.4212),
(7,  'Adventure', 'Upscale',   'Summer', 0.74, 0.12, 2.4,  97000.00,  660, 0.22, 0.3, 9.5, 3.9, 3.2, 4.8, 0, 1, 30, 50.0657, -5.7138),
(8,  'Leisure',   'Upscale',   'Summer', 0.79, 0.10, 2.7, 108000.00,  940, 0.27, 0.2, 2.1, 4.1, 3.9, 4.2, 1, 1, 48, 50.8279, -4.5440),
(9,  'Foodie',    'Boutique',  'Spring', 0.84, 0.07, 2.5, 126000.00, 1120, 0.35, 0.1, 0.6, 4.0, 4.0, 4.4, 0, 1, 20, 50.5410, -4.9360),
(10, 'Luxury',    'Resort',    'Summer', 0.93, 0.05, 4.1, 215000.00, 1840, 0.41, 0.1, 1.4, 4.8, 4.3, 4.7, 1, 1, 72, 50.2110, -5.4800);
