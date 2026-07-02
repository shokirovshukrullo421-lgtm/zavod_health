-- ================================================
-- Zavod / Karyer Xodimlari Sog'liq Monitoring Portali
-- DB Schema v2
-- ================================================
-- Eslatma:
-- - Hozirgi versiya faqat kirish qurilmasidan keladigan real
--   ma'lumotlarni qamrab oladi (harorat, niqob).
-- - Qaror avtomatik emas: shifokor portal orqali yakuniy
--   qarorni tasdiqlaydi (status = 'allowed' / 'medical_check').
-- - Qon bosimi, stress, SpO2 kabi ko'rsatkichlar uchun hozircha
--   manba yo'q, shuning uchun ular bu sxemaga kiritilmagan.
--   Kelajakda yangi manba paydo bo'lganda, mavjud jadvallarni
--   o'zgartirmasdan, yangi jadval qo'shish orqali kengaytiriladi.
-- ================================================


-- ================================================
-- 1. TASHKILIY TUZILMA
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


-- ================================================
-- 2. XODIMLAR (zavod ishchilari — skanerlanadigan, portalga kirmaydigan)
-- ================================================

CREATE TABLE employees (
    id SERIAL PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    position TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,   -- soft delete: ishdan ketganlar shu yerda false bo'ladi
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Xodim - Bo'lim bog'lanishi (ko'p-ko'pga: bitta xodim bir nechta bo'limga tegishli bo'lishi mumkin)
CREATE TABLE employee_departments (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES employees(id),
    department_id INTEGER NOT NULL REFERENCES departments(id)
);


-- ================================================
-- 3. PORTAL FOYDALANUVCHILARI (shifokor, bo'lim mas'uli, admin)
-- ================================================
-- Eslatma: users va employees mustaqil ro'yxatlar, hech qanday bog'lanish yo'q.

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    full_name TEXT NOT NULL,
    login TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('doctor', 'manager', 'admin')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Shifokor qaysi karyer(lar)ga tayinlangan (har karyerda alohida punkt)
CREATE TABLE user_career_assignments (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    career_id INTEGER NOT NULL REFERENCES careers(id)
);

-- Bo'lim mas'uli/rahbar qaysi bo'lim(lar)ga tayinlangan (ko'p-ko'pga)
CREATE TABLE user_department_assignments (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    department_id INTEGER NOT NULL REFERENCES departments(id)
);


-- ================================================
-- 4. QURILMALAR
-- ================================================

CREATE TABLE devices (
    id SERIAL PRIMARY KEY,
    department_id INTEGER NOT NULL REFERENCES departments(id),
    device_code TEXT NOT NULL
);


-- ================================================
-- 5. KIRISH HODISALARI (asosiy jarayon)
-- ================================================
-- Append-only jadval: oylar/yillar davomidagi tarix shu jadvalda
-- avtomatik to'planib boradi.
--
-- Oqim:
--   1. Qurilma xodimni taniydi -> status = 'pending' bilan yozuv yaratiladi
--   2. Shifokor portalda ko'radi (kerak bo'lsa avtomatik ogohlantirish bilan)
--   3. Shifokor tasdiqlaydi -> status = 'allowed' yoki 'medical_check'

CREATE TABLE access_events (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES employees(id),
    device_id INTEGER NOT NULL REFERENCES devices(id),
    auth_method TEXT NOT NULL CHECK (auth_method IN ('face', 'fingerprint')),
    scanned_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Qurilmadan kelgan ko'rsatkichlar
    temperature NUMERIC(4,1),          -- shifokor qaroriga asos bo'ladi
    mask_on BOOLEAN,                   -- faqat statistika uchun, qarorga ta'sir qilmaydi

    -- Shifokor tasdig'i
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'allowed', 'medical_check')),
    reviewed_by INTEGER REFERENCES users(id),   -- qaysi shifokor tasdiqladi
    reviewed_at TIMESTAMP,
    doctor_note TEXT
);


-- ================================================
-- 6. TANILMAGAN URINISHLAR
-- ================================================
-- Qurilma xodimni tanimagan holatlar uchun minimal yozuv.
-- Qurilma imkoniyati aniqlanganda (masalan vaqtinchalik ID yoki
-- snapshot bera olsa), bu jadvalga yangi ustun qo'shiladi.

CREATE TABLE unrecognized_attempts (
    id SERIAL PRIMARY KEY,
    device_id INTEGER NOT NULL REFERENCES devices(id),
    attempted_at TIMESTAMP NOT NULL DEFAULT NOW(),
    note TEXT
);


-- ================================================
-- 7. XABARLAR (portal ichidagi bildirishnomalar)
-- ================================================
-- Masalan: shifokor "bazada yo'q xodim keldi" deb bo'lim
-- mas'uliga xabar yuboradi. Hozircha faqat portal ichida;
-- email/SMS integratsiyasi kelajak rejasi.

CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    from_user_id INTEGER NOT NULL REFERENCES users(id),
    to_user_id INTEGER NOT NULL REFERENCES users(id),
    message_text TEXT NOT NULL,
    related_employee_id INTEGER REFERENCES employees(id),  -- ixtiyoriy, qaysi xodim haqida
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    is_read BOOLEAN NOT NULL DEFAULT FALSE
);


-- ================================================
-- 8. CHEGARA QIYMATLARI (sozlanadigan me'yor)
-- ================================================
-- Masalan harorat uchun max_value = 37.0. Portal shu qiymat
-- bilan solishtirib, shifokorga avtomatik ogohlantirish ko'rsatadi.
-- Yakuniy qarorni baribir shifokor tasdiqlaydi (access_events.status).

CREATE TABLE thresholds (
    id SERIAL PRIMARY KEY,
    metric_name TEXT NOT NULL,         -- masalan 'temperature'
    max_value NUMERIC NOT NULL,
    updated_by INTEGER REFERENCES users(id),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Boshlang'ich chegara qiymati
INSERT INTO thresholds (metric_name, max_value) VALUES ('temperature', 37.0);
