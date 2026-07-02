-- ================================================
-- Zavod / Karyer Xodimlari Sog'liq Monitoring Tizimi
-- DB Schema v1
-- ================================================
-- Eslatma: hozirgi versiya faqat kirish qurilmasidan
-- keladigan real ma'lumotlarni qamrab oladi (harorat, niqob).
-- Qon bosimi, stress, SpO2 kabi ko'rsatkichlar uchun hozircha
-- manba yo'q, shuning uchun ular bu sxemaga kiritilmagan.
-- Kelajakda yangi manba paydo bo'lganda, mavjud jadvallarni
-- o'zgartirmasdan, yangi jadval qo'shish orqali kengaytiriladi.
-- ================================================

-- Karyerlar
CREATE TABLE careers (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL
);

-- Bo'limlar (bir darajali, ichma-ich emas)
CREATE TABLE departments (
    id SERIAL PRIMARY KEY,
    career_id INTEGER NOT NULL REFERENCES careers(id),
    name TEXT NOT NULL
);

-- Xodimlar
CREATE TABLE employees (
    id SERIAL PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    position TEXT
);

-- Xodim - Bo'lim bog'lanishi (ko'p-ko'pga: bitta xodim bir nechta bo'limga tegishli bo'lishi mumkin)
CREATE TABLE employee_departments (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES employees(id),
    department_id INTEGER NOT NULL REFERENCES departments(id)
);

-- Qurilmalar (har bo'limda alohida qurilma)
CREATE TABLE devices (
    id SERIAL PRIMARY KEY,
    department_id INTEGER NOT NULL REFERENCES departments(id),
    device_code TEXT NOT NULL
);

-- Kirish hodisalari (faqat tanilgan xodimlar uchun; "tanimadi" holati hozircha yozilmaydi)
-- Append-only jadval: oylar/yillar davomidagi tarix shu jadvalda avtomatik to'planib boradi.
CREATE TABLE access_events (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES employees(id),
    device_id INTEGER NOT NULL REFERENCES devices(id),
    auth_method TEXT NOT NULL CHECK (auth_method IN ('face', 'fingerprint')),
    scanned_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Statistik/qaror uchun ko'rsatkichlar
    temperature NUMERIC(4,1),          -- qarorga ta'sir qiladi (chegara: 37.0°C)
    mask_on BOOLEAN,                   -- faqat statistika, qarorga ta'sir qilmaydi

    -- Qaror (harorat asosida hisoblanadi)
    decision TEXT NOT NULL CHECK (decision IN ('allowed', 'medical_check')),
    reason TEXT                        -- masalan: 'high_temperature'; ruxsat etilgan bo'lsa NULL
);
