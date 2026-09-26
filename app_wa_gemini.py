import requests
import streamlit as st

# Konfigurasi Halaman Dashboard NOC
st.set_page_config(
    page_title="NOC Multi-Customer Helpdesk", page_icon="🌐", layout="wide"
)

st.title("🌐 NOC Helpdesk & Multi-Customer WhatsApp Bot")
st.markdown(
    "Sistem otomatis pendamping NOC untuk menangani banyak pelanggan secara"
    " fleksibel."
)

# Sidebar untuk Pengaturan Global & Pilih Pelanggan Aktif
with st.sidebar:
  st.header("⚙️ Konfigurasi Sistem")
  RAILWAY_URL = st.text_input(
      "Railway URL",
      value="https://wa-gateway-production-b3e5.up.railway.app/send",
  )
  GEMINI_API_KEY = st.text_input(
      "Gemini API Key",
      value="",
      type="password",
  )

  st.markdown("---")
  st.header("👥 Pelanggan Aktif")
  # Input dinamis untuk nomor pelanggan yang sedang dilayani
  current_customer = st.text_input(
      "Nomor WA Pelanggan Saat Ini:",
      value="6285694291160",
      help=(
          "Ubah nomor ini sesuai dengan pelanggan yang sedang melakukan"
          " chat/kendala."
      ),
  )

  if st.button("Reset Sesi Pelanggan Ini"):
    st.session_state.messages = []
    st.session_state.sop_step = 0
    st.rerun()

# Inisialisasi riwayat chat
if "messages" not in st.session_state:
  st.session_state.messages = [{
      "role": "assistant",
      "content": (
          f"Halo! Terhubung dengan Layanan Bantuan NOC untuk nomor"
          f" **{current_customer}**. Ada kendala internet apa yang sedang"
          " dialami? (Ketik 'mulai' untuk menjalankan SOP)"
      ),
  }]

if "sop_step" not in st.session_state:
  st.session_state.sop_step = 0

# Tampilkan informasi pelanggan aktif di bagian atas chat
st.info(f"💬 Sedang berinteraksi dengan Pelanggan: **{current_customer}**")

# Tampilkan riwayat chat di UI
for message in st.session_state.messages:
  with st.chat_message(message["role"]):
    st.markdown(message["content"])


# Fungsi kirim pesan ke WA via Railway
def kirim_ke_wa(nomor, pesan):
  payload_railway = {"target": nomor, "message": pesan}
  try:
    response = requests.post(RAILWAY_URL, json=payload_railway)
    return response.status_code == 200
  except Exception as e:
    print(f"Error kirim WA: {e}")
    return False


# Input chat dari user / simulasi balasan
if prompt := st.chat_input(
    f"Ketik balasan untuk pelanggan {current_customer}..."
):
  # Tambahkan pesan ke UI
  st.session_state.messages.append({"role": "user", "content": prompt})
  with st.chat_message("user"):
    st.markdown(prompt)

  # Logika SOP NOC Berdasarkan Tahapan
  response_text = ""
  lower_prompt = prompt.lower()

  if (
      st.session_state.sop_step == 0
      and "mulai" in lower_prompt
      or "lapor" in lower_prompt
      or "mati" in lower_prompt
      or "kendala" in lower_prompt
  ):
    st.session_state.sop_step = 1
    response_text = (
        "**[SOP Langkah 1]** Baik Kak, mari kita coba perbaiki secara mandiri"
        " dulu ya. Silakan lakukan **Restart Modem** (cabut kabel"
        " power/adaptor modem, tunggu 1-2 menit, lalu colokkan kembali).\n\nApakah"
        " lampu indikator sudah menyala normal? Ketik **'sudah restart'** jika"
        " sudah dicoba."
    )

  elif (
      st.session_state.sop_step == 1
      and "sudah" in lower_prompt
      or "restart" in lower_prompt
  ):
    st.session_state.sop_step = 2
    response_text = (
        "**[SOP Langkah 2]** Baik. Jika internet masih belum bisa, silakan"
        " periksa fisik modem Anda. **Apakah ada lampu indikator 'LOS' yang"
        " menyala warna merah?**"
    )

  elif st.session_state.sop_step == 2 and (
      "merah" in lower_prompt or "los" in lower_prompt
  ):
    st.session_state.sop_step = 3
    response_text = (
        "**[Eskalasi SOP 2]** Wah, jika lampu LOS menyala merah, artinya ada"
        " gangguan pada jalur kabel optik di luar. Tim teknisi lapangan akan"
        " kami jadwalkan untuk pengecekan lokasi. Mohon tunggu sebentar ya"
        " Kak."
    )

  elif st.session_state.sop_step == 2 and (
      "tidak" in lower_prompt or "normal" in lower_prompt
  ):
    st.session_state.sop_step = 3
    response_text = (
        "**[SOP Langkah 3]** Bagus jika lampu LOS tidak merah. Selanjutnya,"
        " mari kita **cek status koneksi Wi-Fi** di perangkat HP/Laptop Anda."
        " Apakah SSID/nama Wi-Fi Anda terdeteksi dan bisa tersambung?"
    )

  else:
    # Menggunakan Gemini 3.6 Flash dengan instruksi store/lokasi
    url_gemini = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={GEMINI_API_KEY}"
    payload_gemini = {
        "systemInstruction": {
            "parts": [{
                "text": (
                    "Kamu adalah asisten NOC internet yang ramah dan profesional."
                    " Jika pelanggan melaporkan kendala internet atau meminta"
                    " pengecekan jaringan tetapi belum menyebutkan nama"
                    " store/lokasi atau ID pelanggan, mintalah mereka dengan"
                    " sopan untuk menginformasikan nama store atau lokasi cabangnya"
                    " terlebih dahulu."
                )
            }]
        },
        "contents": [{"parts": [{"text": prompt}]}],
    }

    try:
      res_gemini = requests.post(url_gemini, json=payload_gemini)
      data_gemini = res_gemini.json()
      if "candidates" in data_gemini and len(data_gemini["candidates"]) > 0:
        response_text = data_gemini["candidates"][0]["content"]["parts"][0][
            "text"
        ]
      else:
        response_text = (
            "Terima kasih informasinya, mohon infokan nama store atau lokasi"
            " cabangnya terlebih dahulu agar bisa kami bantu cek."
        )
    except Exception:
      response_text = (
          "Terima kasih informasinya, laporan Anda sedang diproses."
      )

  # Tampilkan balasan bot di UI
  st.session_state.messages.append(
      {"role": "assistant", "content": response_text}
  )
  with st.chat_message("assistant"):
    st.markdown(response_text)

  # Kirim otomatis ke nomor pelanggan yang sedang aktif di-input pada sidebar
  sukses_kirim = kirim_ke_wa(current_customer, response_text)
  if sukses_kirim:
    st.toast(f"Pesan terkirim otomatis ke: {current_customer}", icon="🚀")
  else:
    st.error(f"Gagal mengirim pesan ke {current_customer}")