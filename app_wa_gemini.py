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

  api_key_default = ""
  try:
    api_key_default = st.secrets["GEMINI_API_KEY"]
  except Exception:
    api_key_default = ""

  GEMINI_API_KEY = st.text_input(
      "Gemini API Key",
      value=api_key_default,
      type="password",
  )

  st.markdown("---")
  st.header("👥 Pelanggan Aktif")
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
          " f **{current_customer}**. Ada kendala internet apa yang sedang"
          " dialami?"
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
  st.session_state.messages.append({"role": "user", "content": prompt})
  with st.chat_message("user"):
    st.markdown(prompt)

  response_text = ""
  lower_prompt = prompt.lower()

  # Logika SOP NOC dengan bahasa santai sehari-hari (tanpa format formal/SOP kaku)
  if (
      st.session_state.sop_step == 0
      and ("mulai" in lower_prompt
      or "lapor" in lower_prompt
      or "mati" in lower_prompt
      or "kendala" in lower_prompt)
  ):
    st.session_state.sop_step = 1
    response_text = (
        "Halo Kak, coba kita beresin dulu dari rumah ya. Boleh minta"
        " tolong restart modemnya? Caranya cabut kabel adaptor listriknya,"
        " tunggu sekitar 1-2 menit, terus colokin lagi.\n\nKira-kira lampu"
        " indikatornya udah nyala normal belum? Kalau udah dicoba kabari lagi"
        " ya."
    )

  elif (
      st.session_state.sop_step == 1
      and ("sudah" in lower_prompt
      or "restart" in lower_prompt
      or "nyala" in lower_prompt)
  ):
    st.session_state.sop_step = 2
    response_text = (
        "Sip. Kalau internetnya masih belum connect juga, coba dicek fisik"
        " modemnya ya Kak. **Ada lampu indikator yang nyala merah atau tulisannya"
        " LOS nggak?**"
    )

  elif st.session_state.sop_step == 2 and (
      "merah" in lower_prompt or "los" in lower_prompt
  ):
    st.session_state.sop_step = 3
    response_text = (
        "Waduh, kalau lampu LOS-nya nyala merah berarti ada gangguan di kabel"
        " luar nih Kak. Nanti saya bantu teruskan dan jadwalkan tim teknisi"
        " lapangan buat ngecek ke lokasi ya. Ditunggu sebentar ya Kak."
    )

  elif st.session_state.sop_step == 2 and (
      "tidak" in lower_prompt
      or "normal" in lower_prompt
      or "nggak" in lower_prompt
      or "tdk" in lower_prompt
  ):
    st.session_state.sop_step = 3
    response_text = (
        "Oke aman kalau lampu LOS-nya nggak merah. Sekarang coba dicek koneksi"
        " Wi-Fi di HP atau laptopnya, nama Wi-Fi (SSID)-nya kedeteksi nggak"
        " dan bisa nyambung?"
    )

  else:
    # Memperbaiki variabel prompt_user agar mengambil data dari inputan chat asli
    url_gemini = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={GEMINI_API_KEY}"
    
    payload_gemini = {
        "contents": [
            {
                "parts": [
                    {
                        "text": (
                            "Bertindaklah sebagai teknisi NOC yang ramah dan "
                            "menggunakan bahasa obrolan sehari-hari yang santai, "
                            "tidak kaku, dan tidak usah pakai format baku atau "
                            "label SOP seperti '[SOP Langkah 1]'. Langsung berikan "
                            "solusi dengan bahasa obrolan biasa.\n\nPesan dari Pelanggan: "
                            f"{prompt}"
                        )
                    }
                ]
            }
        ]
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
            "Makasih infonya ya Kak, boleh infokan nama store atau lokasi"
            " cabangnya sekalian biar saya gampang cek di sistem?"
        )
    except Exception:
      response_text = (
          "Baik Kak, laporan kendalanya sudah saya catat dan sedang dicek"
          " sebentar ya."
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
