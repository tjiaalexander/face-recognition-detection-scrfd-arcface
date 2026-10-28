from docx import Document
p = r'c:\Kuliah\Semester 5\CV\face-recognition-system\Implementasi_sistem_deteksi_wajah_dan_analisis_demografi_mahasiswa_multi_face_berbasis_real_time_menggunakan_SCRFD_dan_ArcFace.docx'
doc = Document(p)
texts = [para.text for para in doc.paragraphs if para.text.strip()]
print('PARA_COUNT', len(texts))
print('HAS_THEORY', any('Deteksi wajah pada citra digital' in t for t in texts))
print('HAS_PERF', any('Perbandingan performa' in t for t in texts))
print('HAS_ARCFACE', any('ArcFace' in t for t in texts))
