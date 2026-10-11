-- Chinook-style sample database (Postgres port, snake_case).
-- A digital media store: artists -> albums -> tracks, sold via invoices.
-- Explicit integer PKs keep the seed deterministic.

BEGIN;

CREATE TABLE genres (
    genre_id INTEGER PRIMARY KEY,
    name     VARCHAR(120) NOT NULL
);

CREATE TABLE media_types (
    media_type_id INTEGER PRIMARY KEY,
    name          VARCHAR(120) NOT NULL
);

CREATE TABLE artists (
    artist_id INTEGER PRIMARY KEY,
    name      VARCHAR(120) NOT NULL
);

CREATE TABLE albums (
    album_id  INTEGER PRIMARY KEY,
    title     VARCHAR(160) NOT NULL,
    artist_id INTEGER NOT NULL REFERENCES artists(artist_id)
);

CREATE TABLE tracks (
    track_id      INTEGER PRIMARY KEY,
    name          VARCHAR(200) NOT NULL,
    album_id      INTEGER REFERENCES albums(album_id),
    media_type_id INTEGER NOT NULL REFERENCES media_types(media_type_id),
    genre_id      INTEGER REFERENCES genres(genre_id),
    composer      VARCHAR(220),
    milliseconds  INTEGER NOT NULL,
    bytes         INTEGER,
    unit_price    NUMERIC(10, 2) NOT NULL
);

CREATE TABLE employees (
    employee_id INTEGER PRIMARY KEY,
    last_name   VARCHAR(40) NOT NULL,
    first_name  VARCHAR(40) NOT NULL,
    title       VARCHAR(60),
    reports_to  INTEGER REFERENCES employees(employee_id),
    hire_date   DATE,
    email       VARCHAR(80)
);

CREATE TABLE customers (
    customer_id    INTEGER PRIMARY KEY,
    first_name     VARCHAR(40) NOT NULL,
    last_name      VARCHAR(40) NOT NULL,
    company        VARCHAR(80),
    city           VARCHAR(60),
    country        VARCHAR(60),
    email          VARCHAR(80) NOT NULL,
    support_rep_id INTEGER REFERENCES employees(employee_id)
);

CREATE TABLE invoices (
    invoice_id       INTEGER PRIMARY KEY,
    customer_id      INTEGER NOT NULL REFERENCES customers(customer_id),
    invoice_date     TIMESTAMP NOT NULL,
    billing_city     VARCHAR(60),
    billing_country  VARCHAR(60),
    total            NUMERIC(10, 2) NOT NULL DEFAULT 0
);

CREATE TABLE invoice_items (
    invoice_item_id INTEGER PRIMARY KEY,
    invoice_id      INTEGER NOT NULL REFERENCES invoices(invoice_id),
    track_id        INTEGER NOT NULL REFERENCES tracks(track_id),
    unit_price      NUMERIC(10, 2) NOT NULL,
    quantity        INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE playlists (
    playlist_id INTEGER PRIMARY KEY,
    name        VARCHAR(120) NOT NULL
);

CREATE TABLE playlist_track (
    playlist_id INTEGER NOT NULL REFERENCES playlists(playlist_id),
    track_id    INTEGER NOT NULL REFERENCES tracks(track_id),
    PRIMARY KEY (playlist_id, track_id)
);

-- ---------------------------------------------------------------------------
-- Dimension data
-- ---------------------------------------------------------------------------

INSERT INTO genres (genre_id, name) VALUES
 (1,'Rock'),(2,'Jazz'),(3,'Metal'),(4,'Pop'),(5,'Classical'),
 (6,'Blues'),(7,'Reggae'),(8,'Hip Hop'),(9,'Electronic'),(10,'Country');

INSERT INTO media_types (media_type_id, name) VALUES
 (1,'MPEG audio file'),(2,'AAC audio file'),(3,'Protected AAC audio file');

INSERT INTO artists (artist_id, name) VALUES
 (1,'AC/DC'),(2,'Miles Davis'),(3,'Metallica'),(4,'Taylor Swift'),
 (5,'Ludwig van Beethoven'),(6,'B.B. King'),(7,'Bob Marley'),
 (8,'Kendrick Lamar'),(9,'Daft Punk'),(10,'Johnny Cash'),
 (11,'Pink Floyd'),(12,'Nina Simone');

INSERT INTO albums (album_id, title, artist_id) VALUES
 (1,'High Voltage',1),
 (2,'Back in Black',1),
 (3,'Kind of Blue',2),
 (4,'Master of Puppets',3),
 (5,'Ride the Lightning',3),
 (6,'1989',4),
 (7,'Folklore',4),
 (8,'Symphony No. 9',5),
 (9,'Symphony No. 5',5),
 (10,'Live in Cook County Jail',6),
 (11,'Legend',7),
 (12,'good kid, m.A.A.d city',8),
 (13,'Discovery',9),
 (14,'Random Access Memories',9),
 (15,'At Folsom Prison',10),
 (16,'The Dark Side of the Moon',11),
 (17,'The Wall',11),
 (18,'I Put a Spell on You',12);

INSERT INTO tracks (track_id, name, album_id, media_type_id, genre_id, composer, milliseconds, bytes, unit_price) VALUES
 (1,'It''s a Long Way to the Top',1,1,1,'Young, Scott',315000,10240000,0.99),
 (2,'The Jack',1,1,1,'AC/DC',352000,11500000,0.99),
 (3,'T.N.T.',1,1,1,'Young, Scott',215000,7000000,0.99),
 (4,'Hells Bells',2,1,1,'AC/DC',312000,10100000,0.99),
 (5,'Back in Black',2,1,1,'AC/DC',255000,8300000,1.29),
 (6,'You Shook Me All Night Long',2,1,1,'AC/DC',210000,6900000,1.29),
 (7,'So What',3,1,2,'Miles Davis',562000,18200000,0.99),
 (8,'Freddie Freeloader',3,1,2,'Miles Davis',589000,19100000,0.99),
 (9,'Blue in Green',3,1,2,'Miles Davis',337000,10900000,0.99),
 (10,'Battery',4,1,3,'Hetfield, Ulrich',312000,10200000,0.99),
 (11,'Master of Puppets',4,1,3,'Hetfield, Ulrich',515000,16800000,1.29),
 (12,'Welcome Home (Sanitarium)',4,1,3,'Hetfield, Ulrich',388000,12600000,0.99),
 (13,'Fight Fire with Fire',5,1,3,'Hetfield, Ulrich',285000,9300000,0.99),
 (14,'Fade to Black',5,1,3,'Hetfield, Ulrich',417000,13600000,1.29),
 (15,'Blank Space',6,2,4,'Taylor Swift',231000,7500000,1.29),
 (16,'Style',6,2,4,'Taylor Swift',231000,7500000,1.29),
 (17,'Shake It Off',6,2,4,'Taylor Swift',219000,7100000,1.29),
 (18,'cardigan',7,2,4,'Taylor Swift',239000,7800000,1.29),
 (19,'exile',7,2,4,'Taylor Swift',285000,9300000,1.29),
 (20,'Ode to Joy',8,1,5,'Beethoven',1440000,46000000,0.99),
 (21,'Symphony No. 9 - Mvt 1',8,1,5,'Beethoven',920000,29800000,0.99),
 (22,'Symphony No. 5 - Mvt 1',9,1,5,'Beethoven',447000,14500000,0.99),
 (23,'The Thrill Is Gone',10,1,6,'B.B. King',311000,10100000,0.99),
 (24,'Every Day I Have the Blues',10,1,6,'B.B. King',278000,9000000,0.99),
 (25,'No Woman No Cry',11,1,7,'Vincent Ford',427000,13900000,0.99),
 (26,'Three Little Birds',11,1,7,'Bob Marley',180000,5900000,0.99),
 (27,'Redemption Song',11,1,7,'Bob Marley',228000,7400000,0.99),
 (28,'Money Trees',12,2,8,'Kendrick Lamar',386000,12500000,1.29),
 (29,'Swimming Pools (Drank)',12,2,8,'Kendrick Lamar',313000,10200000,1.29),
 (30,'Bitch, Don''t Kill My Vibe',12,2,8,'Kendrick Lamar',310000,10100000,1.29),
 (31,'One More Time',13,1,9,'Daft Punk',320000,10400000,0.99),
 (32,'Harder, Better, Faster, Stronger',13,1,9,'Daft Punk',224000,7300000,0.99),
 (33,'Get Lucky',14,1,9,'Daft Punk',369000,12000000,1.29),
 (34,'Instant Crush',14,1,9,'Daft Punk',337000,10900000,1.29),
 (35,'Folsom Prison Blues',15,1,10,'Johnny Cash',168000,5500000,0.99),
 (36,'Ring of Fire',15,1,10,'Johnny Cash',157000,5100000,0.99),
 (37,'Time',16,1,1,'Pink Floyd',413000,13400000,0.99),
 (38,'Money',16,1,1,'Pink Floyd',382000,12400000,0.99),
 (39,'Another Brick in the Wall',17,1,1,'Pink Floyd',239000,7800000,0.99),
 (40,'I Put a Spell on You',18,1,2,'Screamin'' Jay Hawkins',151000,4900000,0.99);

INSERT INTO employees (employee_id, last_name, first_name, title, reports_to, hire_date, email) VALUES
 (1,'Adams','Andrew','General Manager',NULL,'2018-08-14','andrew@chinook.example'),
 (2,'Edwards','Nancy','Sales Manager',1,'2018-05-01','nancy@chinook.example'),
 (3,'Peacock','Jane','Sales Support Agent',2,'2019-04-01','jane@chinook.example'),
 (4,'Park','Margaret','Sales Support Agent',2,'2019-05-03','margaret@chinook.example'),
 (5,'Johnson','Steve','Sales Support Agent',2,'2020-10-17','steve@chinook.example');

INSERT INTO customers (customer_id, first_name, last_name, company, city, country, email, support_rep_id) VALUES
 (1,'Luis','Gonalves','Embraer','So Jos dos Campos','Brazil','luis@example.com',3),
 (2,'Leonie','Khler',NULL,'Stuttgart','Germany','leonie@example.com',4),
 (3,'Franois','Tremblay',NULL,'Montreal','Canada','francois@example.com',5),
 (4,'Bjrn','Hansen',NULL,'Oslo','Norway','bjorn@example.com',3),
 (5,'Frantiek','Wichterlov','JetBrains','Prague','Czech Republic','frantisek@example.com',4),
 (6,'Helena','Hol',NULL,'Prague','Czech Republic','helena@example.com',5),
 (7,'Astrid','Gruber',NULL,'Vienne','Austria','astrid@example.com',3),
 (8,'Daan','Peeters',NULL,'Brussels','Belgium','daan@example.com',4),
 (9,'Kara','Nielsen',NULL,'Copenhagen','Denmark','kara@example.com',5),
 (10,'Eduardo','Martins','Woodstock Music','So Paulo','Brazil','eduardo@example.com',3);

INSERT INTO playlists (playlist_id, name) VALUES
 (1,'Chill Out'),(2,'Workout Metal'),(3,'Late Night Jazz');

-- ---------------------------------------------------------------------------
-- Fact data (generated for volume, kept internally consistent)
-- ---------------------------------------------------------------------------

-- 30 invoices: 3 per customer, spaced across 2023.
INSERT INTO invoices (invoice_id, customer_id, invoice_date, billing_city, billing_country)
SELECT row_number() OVER (ORDER BY c.customer_id, g.n)                       AS invoice_id,
       c.customer_id,
       (DATE '2023-01-05' + ((c.customer_id * 17 + g.n * 40) % 330) * INTERVAL '1 day')::timestamp AS invoice_date,
       c.city,
       c.country
FROM customers c
CROSS JOIN generate_series(0, 2) AS g(n);

-- 3 line items per invoice, deterministically drawn from the track catalogue.
INSERT INTO invoice_items (invoice_item_id, invoice_id, track_id, unit_price, quantity)
SELECT row_number() OVER (ORDER BY i.invoice_id, t.track_id) AS invoice_item_id,
       i.invoice_id,
       t.track_id,
       t.unit_price,
       1
FROM invoices i
CROSS JOIN LATERAL (
    SELECT track_id, unit_price
    FROM tracks
    ORDER BY (track_id * 7 + i.invoice_id * 13) % 40, track_id
    LIMIT 3
) t;

-- Keep each invoice total in sync with its line items.
UPDATE invoices
SET total = agg.s
FROM (
    SELECT invoice_id, SUM(unit_price * quantity) AS s
    FROM invoice_items
    GROUP BY invoice_id
) agg
WHERE invoices.invoice_id = agg.invoice_id;

-- Populate playlists from tracks by genre.
INSERT INTO playlist_track (playlist_id, track_id)
SELECT 1, track_id FROM tracks WHERE genre_id IN (7, 2) LIMIT 8;
INSERT INTO playlist_track (playlist_id, track_id)
SELECT 2, track_id FROM tracks WHERE genre_id IN (3, 1) LIMIT 8;
INSERT INTO playlist_track (playlist_id, track_id)
SELECT 3, track_id FROM tracks WHERE genre_id = 2;

COMMIT;
