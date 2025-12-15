# cleanupapk

Deskripsi singkat:

- Aplikasi Django bagian dari proyek PBO yang menyediakan endpoint dan logika untuk versi APK (cleanupapk).
- Di dalam folder ini terdapat aplikasi Django `apk` dengan model, views, serializer, dan konfigurasi terkait.

Persyaratan lingkungan:

- Python 3.8+ (sesuaikan dengan `env1` jika sudah dibuat)
- Virtual environment (opsional tapi disarankan)
- Dependencies tercantum di requirements atau di environment proyek utama

Instalasi singkat:

1. Buat dan aktifkan virtual environment:

   python -m venv env
   env\Scripts\activate

2. Install dependensi (jika ada `requirements.txt` di root proyek):

   pip install -r requirements.txt

Menjalankan server pengembangan:

1. Pastikan migrasi sudah dibuat/diapply untuk database sqlite yang ada di repo (db.sqlite3):

   python manage.py migrate

2. Jalankan server:

   python manage.py runserver

Catatan migrasi & database:

- Di repo ini terdapat file `db.sqlite3`; jika ingin memulai dari awal, hapus atau ganti file tersebut lalu jalankan `migrate`.
- Jika menambah model baru di `apk`, jalankan `makemigrations` lalu `migrate`.

Struktur penting:

- `apk/` : aplikasi Django utama untuk versi APK (models, views, serializers, urls)
- `manage.py` : skrip manajemen Django
- `db.sqlite3` : database SQLite lokal (jika disertakan)

Kontribusi:

- Buat branch baru untuk fitur atau perbaikan.
- Sertakan deskripsi singkat pada PR dan langkah reproduksi jika ada bug.

Kontak / Penanggung jawab:

- Tambahkan informasi kontak atau pemilik proyek di sini (opsional).

--
File ini dibuat otomatis; sesuaikan instruksi instalasi dan environment sesuai kebutuhan lokal.
