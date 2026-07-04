# Vox Local Story TTS

Web app chạy trên Windows để biến truyện, kịch bản hoặc nội dung TikTok thành audio TTS. Repo này ưu tiên voice CapCut, đặc biệt là **Cô Gái Hoạt Ngôn**, kèm web UI, local API, cache audio, chia truyện dài, emotion tag, subtitle và export pack làm video.

Repo đã được rút gọn theo hướng **Windows-only**. Source Python/web giữ nguyên, còn tooling được gom vào một CLI PowerShell chính:

```powershell
.\vox.bat help
```

## Chạy Nhanh

Mở PowerShell tại thư mục repo rồi chạy:

```powershell
.\vox.bat setup
.\vox.bat key -Label pc-chinh
.\vox.bat run
```

Mở web UI:

```text
http://127.0.0.1:8010
```

Trang API:

```text
http://127.0.0.1:8010/api
```

## CLI Windows

Các lệnh chính:

```powershell
.\vox.bat setup
.\vox.bat install
.\vox.bat setup-capcut
.\vox.bat run
.\vox.bat start
.\vox.bat stop
.\vox.bat status
.\vox.bat key -Label pc-chinh
.\vox.bat autostart-install
.\vox.bat autostart-remove
.\vox.bat build-release
.\vox.bat clean-deploy
```

Ý nghĩa:

- `setup`: tạo `.venv`, cài dependency, tạo `.env` nếu thiếu, clone/update provider CapCut.
- `install`: chỉ tạo `.venv`, cài dependency, tạo `.env` nếu thiếu.
- `setup-capcut`: clone/update `K07VN/capcut-tts-api` vào `providers/capcut-tts-api` và cập nhật `.env`.
- `run`: chạy server foreground trong terminal hiện tại.
- `start`: chạy server nền, ghi log vào `logs\`.
- `stop`: tắt server.
- `status`: xem PID và port đang listen.
- `key`: sinh API key và hash SHA-256 để lưu trong `.env`.
- `autostart-install`: cài Windows Task Scheduler để tự chạy khi đăng nhập.
- `autostart-remove`: gỡ task autostart.
- `build-release`: đóng gói bản Windows clean release.

Có thể override host/port khi chạy:

```powershell
.\vox.bat run -ListenHost 127.0.0.1 -Port 8010
.\vox.bat start -ListenHost 0.0.0.0 -Port 8010
.\vox.bat status -Port 8010
.\vox.bat stop -Port 8010
```

Các script cũ vẫn được giữ như wrapper tương thích và đều gọi về `vox.ps1`:

```text
run-server.ps1
run-server.bat
vox.bat
setup-capcut-k07vn.ps1
scripts\start-server-windows.ps1
scripts\stop-server-windows.ps1
scripts\status-server-windows.ps1
scripts\generate-api-key-windows.ps1
scripts\install-autostart-windows.ps1
scripts\uninstall-autostart-windows.ps1
scripts\build-clean-release-windows.ps1
```

## Cấu Trúc Repo

```text
.
├── app.py                         # ASGI entrypoint: uvicorn app:app
├── vox.ps1                        # Windows CLI chính
├── vox_local/
│   ├── main.py                    # FastAPI routes
│   ├── config.py                  # Đọc cấu hình .env
│   ├── cache.py                   # Cache audio và history
│   ├── models.py                  # API schemas
│   └── providers/
│       ├── manager.py             # Chọn provider/voice
│       ├── capcut_cli.py          # Gọi K07VN/capcut-tts-api
│       └── windows_sapi.py        # Fallback Windows TTS tùy chọn
├── static/                        # Web UI và trang /api
├── providers/                     # Provider ngoài, không commit
├── audio_cache/                   # Cache audio, không commit
├── logs/                          # Log khi chạy nền
├── run/                           # PID khi chạy nền
├── scripts/                       # Wrapper Windows tương thích
├── run-server.ps1
├── run-server.bat
└── setup-capcut-k07vn.ps1
```

## Yêu Cầu

- Windows 10/11.
- PowerShell 5.1 trở lên.
- Python 3.10 trở lên, khuyến nghị Python 3.11 hoặc 3.12.
- Git for Windows.
- Trình duyệt Chrome, Edge hoặc Firefox.
- Internet nếu dùng provider CapCut.

Kiểm tra nhanh:

```powershell
py --version
git --version
```

## Cấu Hình API Key

Sinh key:

```powershell
.\vox.bat key -Label pc-chinh
```

CLI sẽ in ra plain key và hash. Cách khuyến nghị là lưu hash trong `.env`:

```env
LOCAL_API_KEY=
LOCAL_API_KEYS=
LOCAL_API_KEY_HASHES=pc-chinh:<sha256hash-tu-cli>
```

Plain key vẫn phải nhập vào web UI hoặc extension ở ô `X-API-Key`.

## Cấu Hình CapCut

Nếu đã chạy:

```powershell
.\vox.bat setup
```

thì provider CapCut đã được cài. Nếu chỉ muốn cập nhật provider:

```powershell
.\vox.bat setup-capcut
```

Sau khi chạy, `.env` sẽ có các dòng chính:

```env
TTS_PROVIDER=capcut
ALLOW_NETWORK_TTS=true
TTS_FALLBACK_TO_LOCAL=false
CAPCUT_CLIENT_PATH=providers\capcut-tts-api\capcut_common_task_client.py
CAPCUT_PYTHON=.venv\Scripts\python.exe
```

Nếu bạn có device JSON riêng cho provider, đặt file vào repo và cấu hình:

```env
CAPCUT_DEVICE_JSON=capcut_device_windows.json
```

## Chạy Server

Chạy foreground:

```powershell
.\vox.bat run
```

Dừng bằng `Ctrl+C`.

Chạy nền:

```powershell
.\vox.bat start
.\vox.bat status
.\vox.bat stop
```

Log nằm trong:

```text
logs\server.out.log
logs\server.err.log
```

## Dùng Trong LAN

Mặc định server chỉ nghe `127.0.0.1`. Muốn máy khác trong cùng mạng truy cập, sửa `.env`:

```env
HOST=0.0.0.0
PORT=8010
```

Giữ API key mạnh, rồi restart server:

```powershell
.\vox.bat stop
.\vox.bat start
```

Tìm IP máy server:

```powershell
ipconfig
```

Mở firewall bằng PowerShell chạy Administrator, thay subnet theo mạng của bạn:

```powershell
New-NetFirewallRule `
  -DisplayName "Vox Local Story TTS LAN" `
  -Direction Inbound `
  -Protocol TCP `
  -LocalPort 8010 `
  -Action Allow `
  -RemoteAddress 192.168.1.0/24
```

Truy cập từ máy khác:

```text
http://192.168.1.25:8010
```

Không nên port-forward server này ra Internet. Nếu cần truy cập ngoài LAN, dùng VPN như Tailscale hoặc WireGuard.

## Web UI Auth

Mặc định `WEB_AUTH_ENABLED=false` để chạy thử dễ hơn. Khi dùng trong LAN, nên bật:

```env
WEB_AUTH_ENABLED=true
WEB_AUTH_PROVIDERS=api_key
WEB_SESSION_SECRET=<chuoi-ngau-nhien-rat-dai>
WEB_SESSION_HOURS=24
WEB_AUTH_COOKIE_SECURE=false
```

Sau khi đổi `.env`, restart server:

```powershell
.\vox.bat stop
.\vox.bat start
```

## API Cho Extension

Swagger:

```text
http://127.0.0.1:8010/docs
```

Endpoint extension nên đọc đầu tiên:

```text
GET /v1/extension/capabilities
```

Flow khuyên dùng:

1. `GET /health`
2. `GET /v1/voices`
3. `POST /v1/text/prepare`
4. `POST /v1/tts` hoặc `POST /v1/tts/batch`
5. `GET /v1/cache/{cache_id}?filename=...`

Ví dụ tạo audio một block:

```powershell
curl.exe -X POST "http://127.0.0.1:8010/v1/tts" `
  -H "Content-Type: application/json" `
  -H "X-API-Key: <plain-key>" `
  -d "{\"text\":\"Xin chào, đây là đoạn đọc thử.\",\"rate\":1.0}" `
  --output demo.mp3
```

## Đóng Gói Windows Clean Release

```powershell
.\vox.bat build-release
```

Mặc định tạo:

```text
..\vox-local-story-tts-windows
..\vox-local-story-tts-windows.zip
```

Gói clean release có source, README, CLI, wrapper Windows và `.env.example`, nhưng không có dữ liệu local:

- `.env`
- `providers/capcut-tts-api/`
- `audio_cache/` thật
- `logs/`
- `run/`
- `__pycache__/`, `.pytest_cache/`, `*.pyc`
- `capcut_device_windows.json` được copy vào gói nếu file này tồn tại, vì CapCut có thể trả lỗi `-6` khi thiếu device profile.

## Ghi Chú

- Không commit `.env`, `providers/`, `audio_cache/`, `logs/`, `run/`.
- Cache metadata có chứa text đã gửi TTS, nên bảo vệ thư mục repo nếu nội dung nhạy cảm.
- Provider CapCut là network flow bên ngoài, có thể thay đổi theo thời gian.
- Nếu chỉ muốn fallback Windows TTS offline, chỉnh `.env`:

```env
TTS_PROVIDER=local
ALLOW_NETWORK_TTS=false
TTS_FALLBACK_TO_LOCAL=true
```

## Clean Deploy

Lệnh này đưa repo về trạng thái sạch trước khi triển khai lại: xóa `.env`, `.venv`, provider CapCut đã clone, cache audio, logs, PID và pycache; source app vẫn được giữ nguyên. `capcut_device_windows.json` được giữ lại nếu có, vì thiếu file này CapCut có thể trả lỗi `-6`.

Dry-run:

```powershell
.\vox.bat clean-deploy
```

Xóa thật:

```powershell
.\vox.bat clean-deploy -Force
```

Aliases:

```powershell
.\vox.bat clean
.\vox.bat clear
```
#   v o x - l o c a l - s t o r y - t t s - l i n u x  
 