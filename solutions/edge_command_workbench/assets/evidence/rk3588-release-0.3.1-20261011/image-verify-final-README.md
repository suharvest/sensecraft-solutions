# RKLLM image provenance / RKLLM 镜像来源

The `image-verify-final.txt` record is a verification of the current Docker save re-export, not the historical image record. The archive SHA is `32c83291344d8d283c487bff77ee68b5f442e797c1f2b245d72375b451efe745`; its image config SHA is `d7a81c4f8ef3eaa2c21560b2d37939c6088357ec0c1d41c3089ff5fbc3836de9`. The published artifact inventory separately records the archive SHA used for the HF release.

The provenance is supported by the existing raw records in this directory: `bootstrap-run.log`, `bootstrap-reuse-download.txt`, `image-verify-final.txt`, `archive-sha.txt`, `container-info.txt`, and `compose-config-final.yml`. The bootstrap log records the selected files and the image load; the download record preserves the mirror download evidence. No raw record or hash was rewritten for this note.

`image-verify-final.txt` 记录的是当前 Docker save re-export 的校验，不是历史镜像记录。该归档 SHA 为 `32c83291344d8d283c487bff77ee68b5f442e797c1f2b245d72375b451efe745`，镜像 config SHA 为 `d7a81c4f8ef3eaa2c21560b2d37939c6088357ec0c1d41c3089ff5fbc3836de9`。已发布产物的归档 SHA 仍以 HF 发布 inventory 为准。

来源由本目录已有 raw 记录共同支持：`bootstrap-run.log`、`bootstrap-reuse-download.txt`、`image-verify-final.txt`、`archive-sha.txt`、`container-info.txt` 和 `compose-config-final.yml`。bootstrap 日志记录筛选后的文件和镜像加载，download 记录保留镜像下载证据。本说明没有改写原始记录或 hash。
