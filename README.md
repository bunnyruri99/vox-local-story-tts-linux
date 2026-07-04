# Vox Local Story TTS - Linux Deploy

Gói này là bản deploy Linux, tách riêng khỏi bản Windows hiện tại.

## Cài nhanh

```bash
chmod +x ./vox.sh
./vox.sh setup
./vox.sh run
```

Mở:

```text
http://127.0.0.1:8010
```

## Chạy nền

```bash
./vox.sh start
./vox.sh status
./vox.sh stop
```

## API key

Mặc định `.env.example` để trống API key, nên chạy local không cần key. Sinh key nếu dùng LAN:

```bash
./vox.sh key --label server-linux
```

## LAN

Sửa `.env`:

```env
HOST=0.0.0.0
PORT=8010
```

Rồi restart:

```bash
./vox.sh stop
./vox.sh start
```

## CapCut device profile

Gói này giữ `capcut_device_windows.json` vì profile đó đang giúp tránh lỗi CapCut `ret=-6` (`shark block only`). Tên file có chữ Windows nhưng chỉ là device profile JSON được client CapCut đọc qua `CAPCUT_DEVICE_JSON`.

## Clean deploy

```bash
./vox.sh clean-deploy
./vox.sh clean-deploy --force
```
