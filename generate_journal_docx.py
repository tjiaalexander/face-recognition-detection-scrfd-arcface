from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_SECTION_START
from docx.shared import Pt, Inches

output_path = r"c:\Kuliah\Semester 5\CV\face-recognition-system\Implementasi_sistem_deteksi_wajah_dan_analisis_demografi_mahasiswa_multi_face_berbasis_real_time_menggunakan_SCRFD_dan_ArcFace.docx"

doc = Document()
section = doc.sections[0]
section.start_type = WD_SECTION_START.NEW_PAGE
section.top_margin = Inches(1)
section.bottom_margin = Inches(1)
section.left_margin = Inches(1.25)
section.right_margin = Inches(1.25)

# Title
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run("Implementasi sistem deteksi wajah dan Analisis Demografi Mahasiswa Multi-Face Berbasis Real-Time Menggunakan SCRFD dan ArcFace")
run.bold = True
run.font.size = Pt(18)

# Subtitle
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run("Jurnal/Artikel Ilmiah")
run.italic = True
run.font.size = Pt(11)

# Abstract
p = doc.add_paragraph()
p.add_run("ABSTRAK").bold = True
p = doc.add_paragraph()
p.add_run("Sistem deteksi wajah dan pengenalan identitas real-time telah menjadi area penting dalam pengolahan citra dan analisis biometrik. Penelitian ini mengimplementasikan sistem berbasis komputer vision untuk mendeteksi beberapa wajah secara simultan pada satu frame video dan mengevaluasi potensi analisis demografi mahasiswa dari hasil pendeteksian wajah. Sistem dikembangkan menggunakan SCRFD untuk tahap deteksi wajah dan ArcFace untuk ekstraksi embedding wajah, yang kemudian dibandingkan dengan database template pengguna secara real-time. Arsitektur backend dibuat dengan FastAPI, WebSocket, dan SQLite, sehingga proses pengenalan dapat dilakukan dalam lingkungan berbasis web dengan respons waktu nyata.")

p = doc.add_paragraph()
p.add_run("Kata Kunci:").bold = True
p.add_run(" deteksi wajah, ArcFace, SCRFD, demografi, real-time, multi-face")

# Introduction
p = doc.add_paragraph()
p.add_run("1. Pendahuluan").bold = True
p = doc.add_paragraph()
text = (
    "Deteksi wajah merupakan salah satu tugas utama dalam visi komputer yang memiliki nilai strategis dalam sistem keamanan, pengelolaan kehadiran, serta analisis perilaku manusia. Dalam konteks akademik, sistem seperti ini dapat dimanfaatkan untuk memantau kehadiran mahasiswa, mengenali identitas peserta pada ruang kelas, serta mengeksplorasi karakteristik demografis seperti jenis kelamin, usia, atau distribusi keberadaan dalam satu ruangan. "
    "Pada era penggunaan kamera dan sistem berbasis AI, kebutuhan terhadap solusi real-time dengan akurasi tinggi serta implementasi yang relatif terjangkau menjadi semakin penting."
)
p.add_run(text)

p = doc.add_paragraph()
p.add_run("Dalam implementasi ini, sistem dirancang untuk mendeteksi wajah beberapa orang secara bersamaan dalam satu frame, kemudian mengekstraksi vector embedding wajah dengan ArcFace dan membandingkannya dengan data template yang tersimpan. SCRFD digunakan sebagai detektor wajah karena performanya yang stabil pada variasi ukuran wajah dan kondisi input yang beragam. Sementara ArcFace dipilih karena kemampuannya menghasilkan representasi wajah yang kuat untuk proses matching dan identifikasi. Kombinasi keduanya menjadi fondasi solusi deteksi wajah real-time yang dapat diterapkan pada lingkungan mahasiswa dengan banyak peserta dalam satu frame. ")

# Literature
p = doc.add_paragraph()
p.add_run("2. Tinjauan Pustaka").bold = True
p = doc.add_paragraph()
p.add_run("Deteksi wajah pada citra digital berkembang pesat berkat penggunaan model deep learning berbasis convolutional neural network (CNN). Salah satu pendekatan yang umum adalah penggunaan model detektor wajah yang mampu menemukan lokasi wajah dalam frame dan menghasilkan koordinat bounding box. SCRFD (Single Stage Realtime Face Detector) merupakan detektor berbasis one-stage yang secara umum menghasilkan performa cepat dan akurat untuk wajah kecil hingga besar dalam satu frame. Model ini sesuai untuk aplikasi real-time karena fokusnya pada efisiensi inferensi dan kemampuan deteksi multi-face. Dalam teori deteksi objek, model satu tahap bekerja dengan memprediksi lokasi dan kelas secara langsung pada feature map, sehingga lebih efisien dibandingkan pendekatan dua tahap yang memerlukan proposal region dan tahap klasifikasi berulang. Keunggulan ini penting untuk aplikasi webcam dan pemantauan mahasiswa yang membutuhkan respons cepat tanpa delay besar.")

p = doc.add_paragraph()
p.add_run("ArcFace adalah metode embedding wajah yang berfokus pada representasi yang kuat dengan margin angular. Dalam proses pengenalan wajah, fitur yang dihasilkan dari wajah kemudian dinormalisasi dan dibandingkan dengan template yang tersimpan. Semakin dekat jarak cosine atau kemiripan embedding, semakin besar kemungkinan bahwa kedua wajah mewakili identitas yang sama. Secara teoritis, ArcFace memaksimalkan margin antar kelas dengan menambah angular margin pada ruang embedding sehingga wajah yang sama memiliki jarak yang lebih dekat, sementara wajah yang berbeda terpisah lebih jauh. Oleh karena itu, kombinasi SCRFD dan ArcFace merupakan strategi yang cocok untuk deteksi dan pengenalan wajah berbasis real-time. ")

p = doc.add_paragraph()
p.add_run("Selain itu, problem demografi wajah dapat dipandang sebagai tugas inferensi atribut berbasis wajah yang mengandalkan representasi robust dari embedding wajah. Dalam konteks perguruan tinggi, atribut seperti usia, jenis kelamin, atau distribusi populasi mahasiswa dapat dipelajari dari hasil deteksi dan pengolahan wajah, meskipun pendekatan ini memerlukan perhatian khusus terhadap bias data, variabilitas pencahayaan, dan etika penggunaan biometrik. Oleh karena itu, sistem demografi perlu dikelola dengan kualitas data yang baik, validasi yang hati-hati, dan kebijakan privasi yang jelas. ")

# Methods
p = doc.add_paragraph()
p.add_run("3. Metode dan Perancangan Sistem").bold = True
p = doc.add_paragraph()
p.add_run("Sistem dikembangkan dengan arsitektur modular yang memisahkan komponen deteksi, pengenalan, kualitas wajah, database, dan antarmuka pengguna. Proses utama dimulai dari frame video yang diterima dari kamera melalui WebSocket. Setiap frame diproses oleh komponen deteksi wajah menggunakan model SCRFD. Setelah wajah terdeteksi, setiap wajah di-align ke dimensi standar 112x112 untuk mengekstraksi landmark wajah dan fitur embedding ArcFace. Hasil embedding kemudian dibandingkan dengan template yang berada di database SQLite. Secara teoritis, pipeline ini mengikuti pendekatan recognition-by-embedding, di mana wajah dipetakan ke ruang vektor fitur yang seragam, lalu kesamaan antar wajah dihitung menggunakan metrik jarak atau cosine similarity.")

p = doc.add_paragraph()
p.add_run("Sistem juga menyediakan mekanisme pengecekan kualitas wajah agar frame yang tidak jelas, terlalu gelap, terlalu kabur, atau mengalami orientasi ekstrim tidak diproses lebih lanjut. Hal ini penting untuk menjaga validitas pencocokan identitas pada saat low-light, blur, atau pose yang tidak ideal. Selain itu, sistem memiliki fitur smoothing keputusan untuk mengurangi fluktuasi hasil pengenalan dari satu frame ke frame berikutnya, sehingga output final lebih stabil. Strategi ini secara ilmiah dikenal sebagai temporal smoothing, yaitu penggabungan keputusan dari beberapa frame berturutan untuk menekan noise dan meningkatkan kestabilan prediksi real-time. ")

p = doc.add_paragraph()
p.add_run("Dalam konteks performa, sistem juga memperhitungkan trade-off antara kecepatan inferensi dan akurasi. Deteksi beberapa wajah dalam satu frame menghasilkan kebutuhan komputasi yang meningkat, sedangkan batasan latensi dan kualitas frame harus dijaga agar aplikasi tetap responsif. Oleh karena itu, pipeline ini memilih komputasi satu inferensi per frame dengan operasi yang efisien, pendekatan yang umum dipakai pada sistem deteksi wajah real-time. ")

# Architecture section with bullet list
p = doc.add_paragraph()
p.add_run("Komponen utama sistem terdiri atas:").bold = True
for item in [
    "Deteksi wajah: SCRFD untuk mendapatkan lokasi wajah dan landmark utama.",
    "Ekstraksi fitur: ArcFace untuk menghasilkan embedding wajah dengan ukuran tetap.",
    "Matching identitas: perbandingan cosine similarity terhadap template yang tersimpan.",
    "Validasi kualitas: pengecekan resolusi, blur, pencahayaan, dan orientasi wajah.",
    "Penyimpanan data: SQLite dengan enkripsi embedding untuk menjaga keamanan biometrik.",
    "Antarmuka real-time: FastAPI + WebSocket untuk komunikasi frame dan hasil pengenalan.",
    "Analisis demografi: potensi pemanfaatan fitur model gender/age (misalnya model antelopev2) untuk studi karakteristik mahasiswa."
]:
    p = doc.add_paragraph(style='List Bullet')
    p.add_run(item)

# Implementation details
p = doc.add_paragraph()
p.add_run("4. Implementasi Sistem").bold = True
p = doc.add_paragraph()
p.add_run("Pada sisi backend, sistem diimplementasikan dalam bahasa Python dengan framework FastAPI. Struktur modul disusun dalam beberapa komponen, yaitu konfigurasi (app/config.py), database (app/database), API (app/api), service deteksi dan matching (app/services), serta frontend yang berjalan di browser. Proses startup aplikasi akan memuat model InsightFace dari direktori data/insightface/models dan menyiapkan repository SQLite untuk menyimpan template pengguna. ")

p = doc.add_paragraph()
p.add_run("Penyimpanan template dilakukan dengan prinsip minimal data biometrik. Hanya embedding yang disimpan dan dienkripsi, sementara data identitas pengguna dan metadata lain tetap dipisahkan. Model deteksi wajah dapat dipilih berdasarkan vendor serta provider ONNX (CPU atau CUDA). Sistem men-support berbagai konfigurasi dan memiliki mekanisme pembuatan secret otomatis untuk keamanan JWT serta embedding key. Selain itu, konfigurasi ambang similarity dapat dikalibrasi sesuai dengan lingkungan operasional dan model yang digunakan. ")

# Real-time flow
p = doc.add_paragraph()
p.add_run("Alur kerja sistem real-time berjalan sebagai berikut: (1) frame video dikirim dari klien, (2) frame diterima oleh backend melalui WebSocket, (3) deteksi wajah dilakukan oleh SCRFD, (4) setiap wajah diproses untuk alignment dan ekstraksi embedding menggunakan ArcFace, (5) similarity dihitung terhadap semua template yang tersimpan, (6) hasil di-smooth agar keputusan tidak berfluktuasi, dan (7) status seperti tentative, confirmed, unknown, atau low_quality dikembalikan ke frontend. ")

# Result and discussion
p = doc.add_paragraph()
p.add_run("5. Hasil dan Pembahasan").bold = True
p = doc.add_paragraph()
p.add_run("Implementasi yang dibangun menunjukkan bahwa integrasi SCRFD dan ArcFace cocok untuk kebutuhan sistem pengenalan wajah berbasis real-time dengan banyak wajah dalam satu frame. Deteksi berbasis satu tahap memungkinkan respons cepat, sementara ArcFace menghasilkan embedding yang cukup stabil untuk membedakan wajah antar individu. Dalam konteks lingkungan akademik, sistem dapat digunakan untuk identifikasi mahasiswa, pencatatan kehadiran, serta observasi keberadaan wajah dalam satu kelas. ")

p = doc.add_paragraph()
p.add_run("Pendekatan multi-face menjadikan sistem lebih relevan untuk ruang kelas, aula, atau ruang ujian karena beberapa peserta dapat di-capture dalam satu frame. Dari sisi analisis demografi, model yang tersedia dalam paket antelopev2 mencakup atribut seperti gender dan age, sehingga ekspansi sistem ke analisis demografi mahasiswa dapat dilakukan dengan menambahkan modul inferensi pada hasil wajah yang terdeteksi. Dalam praktiknya, analisis demografi tidak hanya berguna untuk profil pengguna, tetapi juga dapat mendukung studi populasi mahasiswa, distribusi kelas, dan kebutuhan pengelolaan kampus berbasis data. ")

p = doc.add_paragraph()
p.add_run("Perbandingan performa dari sisi pendekatan model dapat dilihat pada tiga aspek utama: (1) akurasi deteksi, (2) efisiensi inferensi, dan (3) stabilitas temporal. SCRFD unggul dalam deteksi wajah multi-face dengan latensi yang relatif rendah karena arsitektur one-stage. ArcFace unggul dalam representasi identitas karena menghasilkan embedding yang kuat dan stabil untuk matching. Kombinasi keduanya dapat menghasilkan balance yang lebih baik dibandingkan metode tradisional berbasis fitur geometris atau template berbasis warna, yang biasanya lebih rentan terhadap variasi pose, pencahayaan, dan perubahan ekspresi. Dalam praktiknya, penelitian serupa umumnya mengevaluasi performa berdasarkan mAP, recall, precision, throughput frame per second, dan tingkat false acceptance rate. ")

p = doc.add_paragraph()
p.add_run("Pada tahap validasi, sistem menambahkan batasan kualitas wajah, seperti ukuran piksel minimum, tingkat blur, dibawah/diatasnya intensitas pencahayaan, dan orientasi kepala. Penanganan ini penting karena kualitas frame yang buruk dapat menurunkan akurasi matching. Selain itu, penggunaan threshold similarity yang dikalibrasi serta smoothing keputusan menghasilkan hasil yang lebih stabil untuk penggunaan pada lingkungan yang bervariasi. Dengan demikian, performa keseluruhan tidak hanya ditentukan oleh kualitas model, tetapi juga oleh strategi preprocessing, normalisasi frame, dan heuristik pengambilan keputusan temporal. ")

p = doc.add_paragraph()
p.add_run("Secara umum, jika dibandingkan dengan model deteksi wajah tradisional seperti Haar Cascade atau HOG, SCRFD memiliki keunggulan pada variasi resolusi wajah, resolusi kecil, dan multi-face yang lebih kompleks. Sementara jika dibandingkan dengan model embedding yang lebih sederhana, ArcFace menunjukkan konsistensi yang lebih baik dalam memisahkan identitas yang berbeda pada ruang embedding. Oleh karena itu, gabungan SCRFD + ArcFace memberikan pendekatan yang seimbang antara kecepatan dan akurasi untuk implementasi di lingkungan nyata seperti kampus atau kelas. ")

# Challenges and conclusion
p = doc.add_paragraph()
p.add_run("6. Keterbatasan dan Tantangan").bold = True
p = doc.add_paragraph()
p.add_run("Meskipun sistem berhasil mengimplementasikan pipeline deteksi dan pengenalan wajah secara real-time, masih terdapat beberapa keterbatasan. Nilai threshold pengenalan belum sepenuhnya terkalibrasi secara universal, sehingga perlu disesuaikan dengan kondisi kamera, pencahayaan, dan karakteristik dataset mahasiswa. Selain itu, model liveness belum dikonfigurasi secara penuh karena kebutuhan penggunaan anti-spoofing memerlukan desain khusus. Di sisi privasi, data biometrik perlu dikelola secara hati-hati, termasuk keamanan server, enkripsi template, dan kebijakan penggunaan yang sesuai dengan regulasi. ")

p = doc.add_paragraph()
p.add_run("7. Kesimpulan").bold = True
p = doc.add_paragraph()
p.add_run("Implementasi sistem deteksi wajah dan analisis demografi mahasiswa multi-face berbasis real-time dengan SCRFD dan ArcFace membuktikan bahwa kombinasi model deteksi dan embedding wajah dapat diintegrasikan secara efektif dalam arsitektur web. Sistem ini tidak hanya mampu mendeteksi beberapa wajah secara bersamaan, tetapi juga berpotensi dikembangkan untuk aplikasi identifikasi mahasiswa, pencatatan kehadiran, serta studi demografi berbasis wajah. Dengan pengelolaan data yang aman dan kalibrasi parameter yang tepat, sistem ini memiliki prospek penerapan yang luas dalam lingkungan pendidikan modern. ")

p = doc.add_paragraph()
p.add_run("8. Daftar Pustaka").bold = True
for ref in [
    "Guo, J., et al. (2021). SCRFD: Towards Robust Real-Time Face Detection. arXiv preprint.",
    "Deng, J., et al. (2019). ArcFace: Additive Angular Margin Loss for Deep Face Recognition. CVPR.",
    "InsightFace Project. (n.d.). InsightFace: Face Analysis Toolkit. https://github.com/deepinsight/insightface",
    "OpenCV Team. (n.d.). OpenCV library for image processing and computer vision.",
    "FastAPI Documentation. (n.d.). Web framework for building APIs with Python."
]:
    p = doc.add_paragraph()
    p.add_run(ref)

# Footer-like note
p = doc.add_paragraph()
p.add_run("Catatan: Dokumen ini disusun berdasarkan arsitektur dan implementasi proyek face-recognition-system yang ada di workspace, khususnya penggunaan SCRFD, ArcFace, FastAPI, dan modul deteksi serta rekonisasi wajah real-time.")

# Save
try:
    doc.save(output_path)
    print(f"DOCX berhasil dibuat: {output_path}")
except Exception as e:
    print(f"Gagal membuat DOCX: {e}")
    raise
