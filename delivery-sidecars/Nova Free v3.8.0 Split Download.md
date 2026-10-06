# Nova Free 3.8.0: split download

Download both parts into the same folder, keeping these exact filenames:

- `Nova the Optimal AI Free v3.8.0.zip.001` (94.4 MB)
- `Nova the Optimal AI Free v3.8.0.zip.002` (93.4 MB)

They are two pieces of the complete edition. Both are required.

## Recreate the normal ZIP on Windows

1. Download `Nova the Optimal AI Free v3.8.0 Reassemble.zip` beside both parts.
2. Right-click that small helper ZIP and choose **Extract All**. Keep the suggested folder beside your downloads.
3. Open the extracted folder and double-click `Reassemble Nova Free.cmd`.
4. Wait for **Reassembled and verified**, or **Already reassembled and verified**. The normal `Nova the Optimal AI Free v3.8.0.zip` appears beside the two parts.

Attach or reference that ordinary ZIP in your harness or Chat project and say, "Install this Augment." You can also extract it normally with Windows' **Extract All**.

The helper checks both downloaded parts and the completed ZIP. A missing part, incomplete download or checksum mismatch names the file to download again. Keep the filenames unchanged. An existing different ZIP is left untouched; move it aside before retrying. The helper also works when placed directly beside the parts.

## Open the split archive directly

With 7-Zip installed, open `.zip.001` and extract the complete edition. 7-Zip reads `.zip.002` automatically from the same folder. Opening `.zip.002` alone will not work.

On macOS or Linux, join the parts in a terminal in their folder:

```sh
cat 'Nova the Optimal AI Free v3.8.0.zip.001' 'Nova the Optimal AI Free v3.8.0.zip.002' > 'Nova the Optimal AI Free v3.8.0.zip'
```

Verify the normal ZIP with `shasum -a 256 'Nova the Optimal AI Free v3.8.0.zip'` on macOS, or `sha256sum 'Nova the Optimal AI Free v3.8.0.zip'` on Linux. Expected SHA-256:

```text
dacda6cb18c054081299c9f42650f4ce0b956a437ea58a3d2c1346939742777f
```

The [ordinary ZIP on GitHub](https://github.com/Stunspot/nova-the-optimal-ai-mind/releases/download/v3.8.0/nova-the-optimal-ai-free-3.8.0.zip) is also available as a single download.
