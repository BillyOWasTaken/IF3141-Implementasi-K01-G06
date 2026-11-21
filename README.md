# Sistem B2B Agent Order & Custom Pricing Engine — Kintakun

Implementasi sistem informasi Tugas Besar **IF3141 Sistem Informasi 2026/2027** berbasis **Odoo 17 Community** dan **PostgreSQL 18** yang dijalankan melalui Docker.

## Identitas Kelompok

**Kelompok 06 — Kelas K01**
Dosen Pengampu: Dr. Lenny Putri Yulianti, S.T., M.T.

| NIM | Nama |
|---|---|
| 13524121 | Billy Ontoseno Irawan |
| 13524055 | Junior Natra Situmorang |
| 13523016 | Clarissa Nethania Tambunan |
| 13524049 | Arina Azka |
| 13524127 | Fazri Arrashyi Putra |
| 13524019 | Kevin Wirya Valerian |

## Nama Sistem dan Perusahaan

- **Perusahaan:** Kintakun — produsen dan peritel perlengkapan tidur (sprei, bedcover, selimut) di Kabupaten Bandung yang mendistribusikan produknya melalui jaringan agen B2B dan marketplace.
- **Sistem:** B2B Agent Order & Custom Pricing Engine, modul tambahan pada ERP Kintakun.

## Deskripsi Sistem

Kintakun menjual sebagian besar produknya secara grosir kepada agen resmi di berbagai kota. Selama ini pesanan agen masuk lewat WhatsApp, lalu Staf Sales mencatatnya dan menghitung harga khusus secara manual di Excel. Agen reguler mendapat potongan 5%, agen prioritas 7%, ditambah promo musiman dan kuota eksklusif per wilayah. Cara ini rawan salah hitung, tidak memberi prioritas yang jelas bagi agen prioritas di gudang, dan sering menimbulkan salah kirim karena barang tidak diperiksa terhadap rincian pesanan sebelum surat jalan terbit. Akibatnya data penjualan, stok, dan piutang di divisi Sales, Inventory, dan Finance tidak sinkron.

Sistem ini menjawab masalah tersebut dengan memadukan modul bawaan Odoo (Sales, Purchase, Inventory, Invoicing, Contacts) dengan dua modul kustom. `kintakun_base` menyediakan data master agen, katalog motif dan ukuran, delapan peran pengguna, dan kerangka menu. `kintakun_b2b_pricing` adalah modul Custom Add-On From Scratch yang menambahkan pengajuan aturan harga berjenjang dengan persetujuan Direktur Utama. Setelah disetujui, aturan tersebut otomatis mengaktifkan pricelist agen.

Modul ini juga menangani alur pesanan sampai keuangan:

- kalkulasi diskon otomatis yang tidak bisa diubah manual, beserta penahanan pesanan yang melampaui kuota wilayah;
- antrean pengiriman yang menempatkan agen prioritas di urutan teratas;
- pemeriksaan fisik barang (fulfillment check) yang mengunci tombol Validate sampai motif, ukuran, dan kuantitas sesuai pesanan;
- setelah surat jalan terbit, pemotongan stok, pembuatan draf faktur piutang, dan pencatatan jejak sinkronisasi terjadi otomatis.

Hasilnya, setiap divisi bekerja dari data yang sama secara real-time.

### Fitur

| ID | Fitur | Kebutuhan / Use Case | Layar |
|---|---|---|---|
| F-01 | Autentikasi & hak akses berbasis peran (8 aktor) | FR-06 / UC-06 | P-01 Login, P-08 UserAccessConfigView |
| F-02 | Data master agen & aturan harga berjenjang dengan persetujuan Direktur | FR-06 / UC-06 | P-02 CustomerMasterView, P-03 PricelistConfigView |
| F-03 | Pencatatan pesanan agen via quick-entry katalog motif & ukuran | FR-01 / UC-01 | P-04 SalesOrderFormView |
| F-04 | Kalkulasi otomatis harga khusus, diskon bertingkat, & validasi kuota wilayah | FR-02 / UC-02 | P-04 SalesOrderFormView |
| F-05 | Penerbitan SO & antrean prioritas pengiriman (Priority Star) | FR-03 / UC-03 | P-05 DeliveryPickingListView |
| F-06 | Order fulfillment check & penerbitan surat jalan | FR-04 / UC-04 | P-06 DeliveryFulfillmentView |
| F-07 | Sinkronisasi stok, faktur piutang, & dasbor lintas divisi | FR-05 / UC-05 | P-07 CustomerInvoiceView, P-08 InventoryAccountingView |

## Kredensial

Seluruh akun dibuat otomatis saat modul dipasang. Kredensial ini hanya untuk development dan demo.

| Peran | Login | Password | Fungsi utama |
|---|---|---|---|
| Administrator | `admin` | `admin` | Seluruh menu dan pengaturan |
| Staf Sales | `staf_sales` | `kintakun123` | Quick-entry pesanan agen, konfirmasi SO |
| Manajer Sales | `manajer_sales` | `kintakun123` | Mengusulkan aturan harga, kelola tier agen |
| Direktur Utama | `direktur` | `kintakun123` | Menyetujui/menolak aturan harga, memantau semua divisi |
| Staf Inventory | `staf_inventory` | `kintakun123` | Antrean pengiriman, fulfillment check, Validate |
| Manajer Inventory | `manajer_inventory` | `kintakun123` | Pemantauan stok dan status pemenuhan |
| Manajer Procurement | `manajer_procurement` | `kintakun123` | Purchase Order, kebutuhan pengadaan |
| Manajer Finance | `manajer_finance` | `kintakun123` | Faktur, pembayaran, jurnal, piutang |
| Manajer IT | `manajer_it` | `kintakun123` | Pengguna dan role |

## Cara Menjalankan Sistem

### Prasyarat

- Docker dengan `docker compose` v2 (Docker Desktop di Windows/Mac)
- Git
- Port 8069 kosong (dapat diganti lewat `ODOO_PORT` di `.env`)

### 1. Clone repositori dan siapkan `.env`

```bash
git clone https://github.com/<akun>/IF3141-Implementasi-K01-G06.git
cd IF3141-Implementasi-K01-G06
cp .env.example .env        # Windows: copy .env.example .env
```

Buka `.env` lalu ganti nilai `POSTGRES_PASSWORD`.

### 2. Pasang modul Kintakun

```bash
docker compose run --rm web odoo -d odoo_app -i kintakun_b2b_pricing --stop-after-init --without-demo=all
```

Perintah ini membuat database `odoo_app` dan memasang Sales, Purchase, Inventory, Invoicing, lokalisasi Indonesia (bagan akun, Rupiah), `kintakun_base`, dan `kintakun_b2b_pricing` beserta data master dan akun pengguna. Prosesnya 2–4 menit.

Hasil yang diharapkan, baris terakhir log:

```text
... INFO odoo_app odoo.modules.loading: Modules loaded.
```

Satu baris `WARNING ... Incorrect usage of try_loading` saat instalasi wajar dan tidak perlu ditindaklanjuti.

### 3. Jalankan server

```bash
docker compose up -d
```

Hasil yang diharapkan:

```text
 ✔ Container if3141-...-db-1   Healthy
 ✔ Container if3141-...-web-1  Started
```

### 4. Login

Buka http://localhost:8069 dan login memakai salah satu akun pada tabel kredensial.

![Halaman login](docs/screenshots/01-login.png)

Setelah login, buka aplikasi **Kintakun B2B** dari ikon menu kiri atas. Menu yang tampil menyesuaikan role pengguna.

![Menu Kintakun B2B](docs/screenshots/02-menu-kintakun.png)

### 5. Mengisi stok awal melalui Purchase Order

Data master belum berisi stok, jadi stok diisi lewat proses pengadaan.

1. Login `manajer_procurement` → **Pengadaan → Permintaan Penawaran (RFQ) → New**.
2. Pilih vendor, tambahkan produk sprei/bedcover beserta kuantitas, lalu **Confirm Order**.
3. Login `staf_inventory` → **Gudang → Penerimaan Barang**, buka penerimaan dari PO tersebut, lalu **Validate**.

![Purchase Order terkonfirmasi](docs/screenshots/04-purchase-order.png)

Hasil yang diharapkan: stok produk bertambah dan terlihat di **Monitoring → Stok & Pemenuhan** maupun kolom **Stok Tersedia** pada pesanan agen.

## Panduan Penggunaan per Fitur

Urutan di bawah mengikuti alur demo dari awal sampai akhir. Kotak merah pada gambar menandai bagian yang diperhatikan.

### F-01 — Hak akses berbasis peran

Login `manajer_it` → ikon menu → **Settings → Users & Companies → Users**. Pilih pengguna, lalu buka tab **Role Kintakun** dan pilih satu dari delapan role. Hak akses Sales, Purchase, Inventory, dan Accounting ikut menyesuaikan.

![Pemilihan role pengguna](docs/screenshots/03-hak-akses-role.png)

### F-02 — Data master agen & persetujuan aturan harga

1. Login `manajer_sales` → **Data Master → Agen B2B**. Tier agen menentukan pricelist yang dipakai secara otomatis.

   ![Profil agen dan pricelist](docs/screenshots/05-agen-pricelist.png)

2. **Data Master → Aturan Harga → New**. Isi jenis aturan (diskon tier atau promo musiman), tier agen, diskon, kuota per wilayah, dan periode promo, lalu klik **Ajukan Persetujuan**. Parameter langsung terkunci dan aturan belum berlaku.

   ![Daftar aturan harga](docs/screenshots/06-aturan-harga-list.png)
   ![Usulan menunggu persetujuan](docs/screenshots/07-usulan-aturan-harga.png)

3. Login `direktur` → **Data Master → Persetujuan Aturan Harga**. Buka usulan, lalu klik **Setujui** atau isi alasan dan klik **Tolak**.

   ![Persetujuan Direktur](docs/screenshots/08-persetujuan-direktur.png)

4. Aturan yang disetujui langsung memperbarui pricelist agen (tab **Pricelist Aktif**). Aturan yang ditolak tidak berlaku dan menyimpan alasan penolakan.

   ![Aturan disetujui dan pricelist aktif](docs/screenshots/09-aturan-disetujui-pricelist.png)
   ![Aturan ditolak](docs/screenshots/10-aturan-ditolak.png)

### F-03 — Quick-entry pesanan agen

Login `staf_sales` → **Pesanan → Quick-Entry Pesanan Agen**. Pilih agen (hanya agen B2B yang muncul), klik **Add a product**, pilih motif dan ukuran dari katalog, isi kuantitas, lalu **Save**. Kuantitas nol atau negatif ditolak, dan kuantitas di atas stok memunculkan peringatan.

![Form quick-entry](docs/screenshots/11-quick-entry.png)

### F-04 — Kalkulasi harga khusus & kuota wilayah

Setelah agen dipilih, pricelist sesuai tier langsung terpasang dan status menjadi **Pricelist Applied**. Diskon baris terisi otomatis: 5% + promo 3% untuk agen reguler, 7% + promo 3% untuk agen prioritas. Kolom harga dan diskon terkunci.

![Pesanan agen reguler](docs/screenshots/12-pesanan-agen-reguler.png)

Tab **Harga Khusus** merinci aturan yang dipakai dan potongan masing-masing.

![Rincian harga khusus](docs/screenshots/13-rincian-harga-khusus.png)
![Pesanan agen prioritas](docs/screenshots/14-pesanan-agen-prioritas.png)

Jika total pesanan di wilayah agen melampaui kuota aturan, muncul peringatan merah dan tombol **Confirm** menolak pesanan.

![Kuota wilayah terlampaui](docs/screenshots/15-kuota-wilayah-terlampaui.png)

Bila ada aturan baru yang disetujui saat penawaran masih draf, klik **Hitung Ulang Harga**.

### F-05 — Penerbitan SO & antrean prioritas

1. Login `staf_sales`, buka penawaran, lalu klik **Confirm**. Status berubah menjadi Sales Order, nomor antrean terbit, stok direservasi, dan agen prioritas mendapat Priority Star.

   ![SO terbit](docs/screenshots/16-so-terbit-prioritas.png)
   ![Daftar pesanan agen](docs/screenshots/17-daftar-pesanan-agen.png)

2. Login `staf_inventory` → **Gudang → Antrean Pengiriman Prioritas**. Pengiriman agen prioritas berada di urutan teratas walaupun dikonfirmasi belakangan. Pesanan yang melebihi stok tetap terbit, tetapi pengirimannya berstatus *Waiting*.

   ![Antrean pengiriman prioritas](docs/screenshots/18-antrean-pengiriman-prioritas.png)

### F-06 — Fulfillment check & surat jalan

1. Buka pengiriman teratas. Tombol **Validate** belum tersedia; klik **Mulai Pemeriksaan**.

   ![Validate terkunci](docs/screenshots/19-validate-terkunci.png)

2. Pada tab **Fulfillment Check**, isi **Kuantitas Fisik** dan centang **Motif & Ukuran Sesuai**, atau klik **Pindai Barang** dan pindai/ketik barcode atau kode produk. Produk yang tidak ada di SO ditolak.

   ![Pindai barang](docs/screenshots/21-pindai-barang.png)

3. Klik **Selesaikan Pemeriksaan**. Jika ada yang tidak cocok, status menjadi **Tidak Sesuai**, surat jalan ditahan, dan alasannya tercatat di chatter. Ulangi pemeriksaan sampai semua cocok.

   ![Pemeriksaan tidak sesuai](docs/screenshots/20-pemeriksaan-tidak-sesuai.png)
   ![Pemeriksaan lolos](docs/screenshots/22-pemeriksaan-lolos.png)

4. Klik **Validate**. Status menjadi *Done*, stok terpotong, dan **Print → Delivery Slip** mencetak surat jalan.

   ![Surat jalan terbit](docs/screenshots/23-surat-jalan-terbit.png)

### F-07 — Sinkronisasi stok, faktur, & dasbor

1. Saat surat jalan divalidasi, sistem otomatis membuat **draf faktur** dengan nilai sama dengan harga akhir SO. Login `manajer_finance` → **Keuangan → Faktur Agen B2B**.

   ![Draf faktur otomatis](docs/screenshots/24-draf-faktur-otomatis.png)

2. Klik **Confirm**, lalu **Register Payment → Create Payment**. Faktur berstatus *Paid*, dan jurnal piutang serta penjualan terbentuk.

   ![Faktur lunas](docs/screenshots/26-faktur-lunas.png)
   ![Jurnal piutang](docs/screenshots/27-jurnal-piutang.png)

3. **Keuangan → Log Sinkronisasi** mencatat pemotongan stok, pembuatan faktur, pengesahan, dan pembayaran per pesanan. Jika pembuatan faktur gagal, log berstatus *Gagal* dan dapat diulang lewat **Sinkron Ulang**; sistem juga mencoba ulang otomatis tiap 10 menit.

   ![Log sinkronisasi](docs/screenshots/28-log-sinkronisasi.png)

4. Menu **Monitoring** menampilkan dasbor stok dan pesanan terbuka, kebutuhan pengadaan, status pemenuhan, dan piutang per agen.

   ![Pemantauan stok](docs/screenshots/29-monitoring-stok.png)
   ![Piutang per agen](docs/screenshots/30-piutang-per-agen.png)
   ![Status pemenuhan](docs/screenshots/31-status-pemenuhan.png)

## Kesimpulan

Sistem B2B Agent Order & Custom Pricing Engine berhasil diimplementasikan di atas Odoo 17 Community dengan satu modul Custom Add-On From Scratch (`kintakun_b2b_pricing`). Ketujuh fitur F-01 sampai F-07 memenuhi kebutuhan fungsional FR-01 sampai FR-06 dan skenario uji Milestone 4:

- Harga khusus agen dihitung otomatis dari aturan yang telah disetujui Direktur Utama, sehingga potensi salah hitung dan perubahan harga sepihak hilang.
- Kuota eksklusif wilayah ditegakkan sebelum SO terbit.
- Agen prioritas mendapat urutan teratas di gudang.
- Barang tidak dapat keluar sebelum lolos pemeriksaan fisik.
- Stok, faktur piutang, dan pembayaran tersinkron otomatis dengan jejak audit yang dapat ditelusuri.

Seluruh aturan bisnis tersebut diverifikasi oleh 47 automated test dan alur demo lintas peran.

## Saran

1. Menyambungkan pesanan dari WhatsApp atau portal agen secara langsung, agar agen dapat memasukkan pesanan sendiri tanpa perantara Staf Sales.
2. Menambahkan notifikasi otomatis (email atau aktivitas Odoo) kepada Direktur Utama saat ada usulan aturan harga baru.
3. Mencatat cashback agen sebagai nota kredit dan menambahkan laporan umur piutang.
4. Menambahkan peringatan dini slow-moving stock dan dasbor KPI untuk proses bisnis PB-03 dan PB-04.
5. Untuk deployment, memakai `config/odoo.prod.conf.example`, mengganti seluruh password default, dan menjadwalkan backup database.

## Informasi Teknis

### Struktur Repositori

| Path | Isi |
|---|---|
| `custom_addons/kintakun_base/` | Role, data master agen/wilayah/produk, kerangka menu, akun pengguna |
| `custom_addons/kintakun_b2b_pricing/` | Custom Add-On From Scratch: aturan harga, pricelist, pesanan agen, antrean prioritas, fulfillment check, faktur, monitoring |
| `custom_addons/starter_cats/` | Modul contoh dari template |
| `config/` | Konfigurasi Odoo development dan contoh deployment |
| `scripts/` | Skrip backup/restore database |
| `docs/screenshots/` | Screenshot panduan |

### Perintah

| Keperluan | Perintah |
|---|---|
| Mulai / berhenti | `docker compose up -d` / `docker compose down` |
| Lihat log | `docker compose logs -f web` |
| Upgrade modul setelah `git pull` | `docker compose run --rm web odoo -d odoo_app -u kintakun_base --stop-after-init` lalu `docker compose restart web` |
| Menjalankan test | `docker compose run --rm web odoo -d odoo_test -i kintakun_b2b_pricing --test-enable --test-tags /kintakun_base,/kintakun_b2b_pricing --stop-after-init --without-demo=all` |
| Backup / restore | `./scripts/export_db.sh` / `./scripts/import_db.sh` (Windows: `.cmd`) |
| Hapus seluruh data | `docker compose down -v` |

Gunakan `docker compose run --rm web odoo ...`, bukan `exec`, karena hanya `run` yang memasang koneksi database dari `.env`. Untuk menjalankan test kedua kalinya pada `odoo_test` yang sama, ganti `-i` dengan `-u`.

### Troubleshooting

- **`variable is missing a value`**: `.env` belum dibuat.
- **Port 8069 terpakai**: ubah `ODOO_PORT` di `.env`.
- **Menu Kintakun B2B tidak muncul**: pengguna belum memiliki role Kintakun (lihat F-01).
- **"Pricelist agen belum diterapkan"** pada pesanan: belum ada aturan tier yang disetujui untuk tier agen tersebut. Minta Direktur menyetujui, lalu klik **Hitung Ulang Harga**.
- **Muncul dialog SMS saat Validate**: Settings → Inventory → matikan *SMS Confirmation*.
- **Skrip `.sh` error `Permission denied` atau `\r`**: `chmod +x scripts/*.sh`; Windows memakai skrip `.cmd`.
- **Mata uang masih USD**: database dibuat sebelum modul terpasang. Buat ulang database (`docker compose down -v`) lalu ulangi langkah 2.

### Keamanan

Konfigurasi di repositori ini ditujukan untuk development lokal. Untuk deployment, mulai dari `config/odoo.prod.conf.example` (set `admin_passwd`, `list_db = False`, `proxy_mode`, worker, batas memori), jangan memakai `--dev`, dan ganti seluruh password akun demo.
