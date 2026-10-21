// reCamera sidebar panel: device cards, live preview and region editor.
(() => {
  if (customElements.get("recamera-motion-panel")) return;

  const POLL_MS = 1500;

  const TEXT = {
    zh: {
      title: "reCamera",
      subtitle: "Seeed 智能摄像机 · 设备与应用管理",
      loading: "加载中…",
      no_devices: "还没有添加 reCamera",
      no_devices_hint: "请到「设置 → 设备与服务 → 添加集成 → reCamera」添加摄像机",
      load_failed: "无法读取 reCamera 列表",
      retry: "重试",
      add_integration: "打开集成页",
      add_device: "添加设备",
      add_device_title: "添加 reCamera",
      connect_add: "连接并添加",
      cancel: "取消",
      connecting: "正在连接设备…",
      device_added: "设备已添加",
      device_removed: "设备已删除",
      delete_device: "删除设备",
      delete_device_confirm: "将删除该设备及其 HA 实体与事件规则，设备本身不会恢复出厂设置。",
      err_cannot_connect: "无法连接设备，请检查 IP 和网络",
      err_invalid_host: "请输入有效的 IP 地址或主机名",
      err_already_configured: "该设备已添加",
      err_unknown: "未知错误",
      field_host: "IP 地址 / 主机名",
      field_device_name: "设备名称",
      field_api_port: "API 端口",
      field_rtsp_port: "RTSP 端口",
      field_rtsp_stream: "RTSP 流名",
      card_title: "选区运动检测",
      card_open: "打开选区编辑",
      online: "应用在线",
      offline: "应用未上报",
      motion: "运动中",
      idle: "无运动",
      warming: "背景预热中",
      detection_on: "检测已开启",
      detection_off: "检测已关闭",
      zones_none: "未绘制检测区域",
      zones_count: "个检测区域",
      last_motion: "最近告警",
      never: "暂无",
      legacy_hint: "设备端程序版本较旧，不支持事件推送与抓拍，请更新 motion_detection",
      back: "返回",
      refresh: "刷新",
      saved: "已保存",
      save: "保存选区",
      save_failed: "保存失败",
      reset_background: "重建背景",
      background_done: "已重建背景，等待预热",
      enable: "开启检测",
      disable: "暂停检测",
      live: "实时画面",
      stream_hint: "画面由 Home Assistant 从摄像机 JPEG 通道合成",
      stream_error: "实时画面不可用，正在重试…",
      tools: "绘制工具",
      type_include: "检测区域",
      type_exclude: "白名单（忽略）",
      zone_name: "区域名称",
      zone_name_ph: "例如：大门口",
      finish: "完成当前多边形",
      undo: "撤销顶点",
      clear_draft: "取消绘制",
      draw_hint: "在画面上左键依次添加顶点，右键撤销；至少 3 个顶点后可「完成当前多边形」。",
      zones: "区域列表",
      no_zones: "还没有区域，先在画面上画一个检测区域",
      delete_zone: "删除",
      points: "个顶点",
      sensitivity: "灵敏度",
      pixel_threshold: "像素阈值",
      min_motion_pixels: "最小运动像素",
      min_blob_pixels: "最小连通块",
      trigger_frames: "触发帧数",
      clear_frames: "恢复帧数",
      warmup_frames: "预热帧数",
      background_alpha: "背景更新速度",
      foreground_alpha: "前景更新速度",
      stats: "实时状态",
      stat_motion_pixels: "运动像素",
      stat_largest_blob: "最大连通块",
      stat_ratio: "运动占比",
      stat_mask: "有效掩膜像素",
      stat_frames: "累计帧数",
      stat_bbox: "运动框",
      stat_error: "设备错误",
      events: "最近告警",
      no_events: "暂无告警记录",
      event_start: "运动开始",
      event_end: "运动结束",
      notify: "通知与推送",
      ha_notification: "在 Home Assistant 中弹出通知",
      ha_notification_hint: "开启后每次告警会在通知中心留下一条带抓拍图片的消息",
      device_push: "设备主动推送",
      device_push_hint: "关闭后仅依靠轮询，告警延迟约 1 秒",
      push_url: "推送地址",
      push_none: "未检测到可用的 Home Assistant 地址，请在「设置 → 系统 → 网络」填写内部地址",
      push_error: "推送配置失败",
      push_stats: "已推送 / 已接收",
      test_push: "发送测试告警",
      test_push_ok: "测试事件已发出，请查看通知中心",
      preview_fps: "预览帧率",
      automation_hint: "在自动化中可用触发器「事件」→ recamera_motion，或使用仓库中的蓝图推送手机通知",
      confirm_delete: "确认删除该区域？",
      dirty_hint: "有未保存的修改",
      zone_added: "已添加区域，记得点「保存选区」写入设备",
      apps_title: "应用",
      no_apps: "尚未添加应用。粘贴应用的 GitHub 仓库地址，读取仓库根目录的 recamera-app.json。",
      add_repository: "从 GitHub 添加应用",
      repository_url: "GitHub 仓库地址",
      repository_hint: "例如 https://github.com/yyling0101-a11y/recamera_motion_detection。此操作只在 HA 中登记应用；设备端程序仍由 reCamera Solution 安装。",
      repository_added: "应用配置已添加到此设备",
      remove_app: "移除应用",
      remove_app_confirm: "从此设备的 HA 页面移除应用配置？这不会卸载设备上的程序。",
      running_app: "当前应用",
      app_running: "运行中",
      app_stopped: "未检测到应用",
      open_app: "打开",
      launch_app: "启动",
      one_app_hint: "一台设备同一时间只运行一个应用",
      app_region_motion: "选区运动检测",
      app_region_motion_desc: "在画面上绘制检测区域，检测到运动时告警并抓拍",
      reachable: "设备可达",
      unreachable: "设备不可达",
      api_unavailable: "应用接口未运行",
      upload_package: "上传应用包",
      upload_hint: "应用包保存在 HA；请用 reCamera Solution 将应用安装到设备。应用运行后向此设备的推送地址发送事件。",
      package_uploaded: "应用包已保存",
      package_too_large: "应用包不能超过 8 MiB",
      uploaded: "已上传到 HA",
      waiting_app: "等待设备应用上报",
      custom_events: "应用事件",
    },
    en: {
      title: "reCamera",
      subtitle: "Seeed smart camera · device & app management",
      loading: "Loading…",
      no_devices: "No reCamera added yet",
      no_devices_hint: "Go to Settings → Devices & Services → Add integration → reCamera",
      load_failed: "Cannot read the reCamera list",
      retry: "Retry",
      add_integration: "Open integrations",
      add_device: "Add device",
      add_device_title: "Add reCamera",
      connect_add: "Connect & add",
      cancel: "Cancel",
      connecting: "Connecting…",
      device_added: "Device added",
      device_removed: "Device removed",
      delete_device: "Delete device",
      delete_device_confirm: "This removes the device and its HA entities and event rules. The device itself is not factory-reset.",
      err_cannot_connect: "Cannot connect. Check the IP address and network.",
      err_invalid_host: "Enter a valid IP address or hostname",
      err_already_configured: "This device is already added",
      err_unknown: "Unknown error",
      field_host: "IP address / hostname",
      field_device_name: "Device name",
      field_api_port: "API port",
      field_rtsp_port: "RTSP port",
      field_rtsp_stream: "RTSP stream",
      card_title: "Region motion detection",
      card_open: "Open region editor",
      online: "App online",
      offline: "No app signal",
      motion: "Motion",
      idle: "Idle",
      warming: "Warming up",
      detection_on: "Detection on",
      detection_off: "Detection paused",
      zones_none: "No detection zone",
      zones_count: "zone(s)",
      last_motion: "Last alert",
      never: "never",
      legacy_hint: "The camera runs an older motion_detection build without push and snapshots. Please update it.",
      back: "Back",
      refresh: "Refresh",
      saved: "Saved",
      save: "Save regions",
      save_failed: "Save failed",
      reset_background: "Rebuild background",
      background_done: "Background rebuilt, warming up",
      enable: "Enable detection",
      disable: "Pause detection",
      live: "Live view",
      stream_hint: "Frames are composed by Home Assistant from the camera JPEG channel",
      stream_error: "Live view unavailable, retrying…",
      tools: "Drawing tools",
      type_include: "Detection zone",
      type_exclude: "Whitelist (ignore)",
      zone_name: "Zone name",
      zone_name_ph: "e.g. Front door",
      finish: "Finish polygon",
      undo: "Undo point",
      clear_draft: "Cancel drawing",
      draw_hint: "Left click to add vertices, right click to undo. At least 3 points are required.",
      zones: "Zones",
      no_zones: "No zone yet - draw one on the preview",
      delete_zone: "Delete",
      points: "point(s)",
      sensitivity: "Sensitivity",
      pixel_threshold: "Pixel threshold",
      min_motion_pixels: "Min motion pixels",
      min_blob_pixels: "Min blob pixels",
      trigger_frames: "Trigger frames",
      clear_frames: "Clear frames",
      warmup_frames: "Warmup frames",
      background_alpha: "Background alpha",
      foreground_alpha: "Foreground alpha",
      stats: "Live status",
      stat_motion_pixels: "Motion pixels",
      stat_largest_blob: "Largest blob",
      stat_ratio: "Motion ratio",
      stat_mask: "Active mask pixels",
      stat_frames: "Frames",
      stat_bbox: "Bounding box",
      stat_error: "Device error",
      events: "Recent alerts",
      no_events: "No alert yet",
      event_start: "Motion start",
      event_end: "Motion end",
      notify: "Notifications and push",
      ha_notification: "Show a Home Assistant notification",
      ha_notification_hint: "Each alert leaves a notification with the captured frame",
      device_push: "Camera push",
      device_push_hint: "When off, Home Assistant polls only (about 1 s latency)",
      push_url: "Push URL",
      push_none: "No Home Assistant URL detected. Set an internal URL under Settings → System → Network.",
      push_error: "Push setup failed",
      push_stats: "pushed / received",
      test_push: "Send test alert",
      test_push_ok: "Test event sent, check the notification drawer",
      preview_fps: "Preview fps",
      automation_hint: "Use the recamera_motion event trigger in automations, or import the bundled blueprint for phone notifications",
      confirm_delete: "Delete this zone?",
      dirty_hint: "Unsaved changes",
      zone_added: "Zone added - press Save regions to write it to the camera",
      apps_title: "Apps",
      no_apps: "No apps added yet. Paste an app's GitHub repository URL to read recamera-app.json from its root.",
      add_repository: "Add app from GitHub",
      repository_url: "GitHub repository URL",
      repository_hint: "For example https://github.com/yyling0101-a11y/recamera_motion_detection. This registers the app in HA; install the device program with reCamera Solution.",
      repository_added: "App configuration added to this device",
      remove_app: "Remove app",
      remove_app_confirm: "Remove this app configuration from the device in HA? The device program will remain installed.",
      running_app: "Current app",
      app_running: "Running",
      app_stopped: "No app detected",
      open_app: "Open",
      launch_app: "Launch",
      one_app_hint: "A device runs one app at a time",
      app_region_motion: "Region motion detection",
      app_region_motion_desc: "Draw detection zones; get alerts and snapshots on motion",
      reachable: "Device reachable",
      unreachable: "Device unreachable",
      api_unavailable: "App API unavailable",
      upload_package: "Upload app package",
      upload_hint: "The package is stored in HA. Install it on the camera with reCamera Solution, then send events to this device's push URL.",
      package_uploaded: "App package saved",
      package_too_large: "Package must be under 8 MiB",
      uploaded: "Uploaded to HA",
      waiting_app: "Waiting for app events",
      custom_events: "App events",
    },
  };

  const STYLE = `
    :host {
      display: block; height: 100%;
      --card-background-color: #121922;
      --primary-background-color: #0b1016;
      --secondary-background-color: #17212c;
      --primary-text-color: #f4f8fb;
      --secondary-text-color: #8fa2b5;
      --divider-color: #273747;
      --primary-color: #11b6e8;
      --text-primary-color: #fff;
    }
    * { box-sizing: border-box; }
    .wrap {
      height: 100%; overflow: auto; padding: 32px clamp(18px, 3vw, 42px) 100px;
      background: radial-gradient(circle at 78% -8%, rgba(17,182,232,.13), transparent 30%), radial-gradient(circle at 5% 25%, rgba(45,120,255,.09), transparent 28%), var(--primary-background-color);
      color: var(--primary-text-color, #212121);
      font: 14px/1.5 Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
    }
    .view { max-width: 1440px; margin: 0 auto; }
    @media (max-width: 700px) { .wrap { padding: 22px 14px 92px; } }
    .global-language { position: fixed; top: 24px; right: 30px; z-index: 12; }
    .lang-switch {
      display: inline-flex; padding: 3px; border: 1px solid var(--divider-color);
      border-radius: 11px; background: rgba(12,19,27,.88);
      box-shadow: 0 8px 24px rgba(0,0,0,.22); backdrop-filter: blur(10px);
    }
    .lang-switch button {
      border: 0; background: transparent; color: var(--secondary-text-color);
      border-radius: 8px; padding: 7px 11px; cursor: pointer;
      font-size: 12px; font-weight: 700; transition: .18s;
    }
    .lang-switch button:hover { color: #fff; }
    .lang-switch button.active {
      background: linear-gradient(135deg, rgba(17,182,232,.3), rgba(45,120,255,.34));
      color: #fff; box-shadow: 0 2px 9px rgba(17,182,232,.18);
    }
    @media (max-width: 700px) {
      .global-language { top: 14px; right: 14px; }
      .lang-switch button { padding: 6px 9px; }
    }
    .header { display: flex; align-items: center; gap: 12px; margin-bottom: 4px; flex-wrap: wrap; padding-right: 118px; }
    @media (max-width: 700px) { .header { padding-right: 92px; } }
    .header h1 { font-size: clamp(24px,2.4vw,34px); font-weight: 700; letter-spacing: -.035em; margin: 0; }
    .header .sub { color: var(--secondary-text-color, #727272); font-size: 13px; }
    .spacer { flex: 1 1 auto; }
    .cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; margin-top: 16px; }
    .card {
      position: relative;
      background: linear-gradient(145deg, color-mix(in srgb, var(--card-background-color, #fff) 96%, var(--primary-color, #11b6e8) 4%), var(--card-background-color, #fff));
      border: 1px solid var(--divider-color, #e0e0e0); border-radius: 20px; padding: 16px;
      box-shadow: 0 1px 3px rgba(0,0,0,.12); cursor: pointer;
      transition: transform .2s ease, box-shadow .2s ease, border-color .2s ease;
    }
    .card:hover { transform: translateY(-4px); box-shadow: 0 18px 55px rgba(0,0,0,.26); border-color: #38536b; }
    .card h2 { margin: 0 0 4px; font-size: 17px; font-weight: 600; }
    .device-card { padding: 0; overflow: hidden; min-height: 200px; }
    .device-visual {
      height: 94px; display: flex; align-items: center; padding: 0 23px;
      background: linear-gradient(110deg, #10293b, #14364b 55%, #192840);
      border-bottom: 1px solid var(--divider-color, rgba(127,127,127,.18));
    }
    .camera-mark {
      width: 62px; height: 62px; border-radius: 18px; display: grid; place-items: center;
      background: #fff; color: #11b6e8;
      box-shadow: 0 10px 24px color-mix(in srgb, var(--primary-color, #11b6e8) 30%, transparent);
    }
    .camera-mark svg { width: 34px; height: 34px; display: block; }
    .device-body { padding: 20px 21px; }
    .name { font-size: 18px; font-weight: 720; }
    .host { font: 12px/1.4 ui-monospace, SFMono-Regular, Consolas, monospace; color: var(--secondary-text-color, #8fa2b5); margin-top: 4px; }
    .meta { color: var(--secondary-text-color, #727272); font-size: 13px; margin-top: 8px; }
    .chip-row { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 14px; }
    .chips { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 12px; }
    .chip {
      display: inline-flex; align-items: center; gap: 7px;
      border: 1px solid var(--divider-color, #e0e0e0);
      background: color-mix(in srgb, var(--secondary-background-color, #eee) 55%, transparent);
      border-radius: 999px; padding: 4px 10px; font-size: 12px; line-height: 18px;
      color: var(--secondary-text-color, #727272); white-space: nowrap;
    }
    .chip.ok { color: #2e9e5b; border-color: rgba(53,208,127,.4); background: rgba(53,208,127,.12); }
    .chip.warn { color: #b26a00; border-color: rgba(255,184,77,.45); background: rgba(255,184,77,.14); }
    .chip.bad { color: #d24a52; border-color: rgba(255,98,108,.45); background: rgba(255,98,108,.12); }
    .chip.live { color: #fff; border-color: transparent; background: rgba(229,57,53,.9); }
    .dot { width: 7px; height: 7px; border-radius: 50%; background: var(--secondary-text-color, #8fa2b5); display: inline-block; flex: 0 0 auto; }
    .dot.ok { background: #35d07f; box-shadow: 0 0 0 3px rgba(53,208,127,.14); }
    .dot.bad { background: #ff626c; box-shadow: 0 0 0 3px rgba(255,98,108,.14); }
    .dot.warn { background: #ffb84d; box-shadow: 0 0 0 3px rgba(255,184,77,.14); }
    .preview-stage { position: relative; width: 100%; max-width: 720px; max-height: 420px; aspect-ratio: 16 / 9; background: #000; border-radius: 12px; overflow: hidden; margin: 0 auto; }
    .preview-stage img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: contain; display: block; }
    .empty {
      margin-top: 24px; padding: 24px; text-align: center; border-radius: 12px;
      background: var(--card-background-color, #fff); color: var(--secondary-text-color, #727272);
    }
    button {
      font: inherit; border: 0; border-radius: 8px; padding: 8px 14px; cursor: pointer;
      background: var(--primary-color, #03a9f4); color: var(--text-primary-color, #fff);
    }
    button.ghost { background: transparent; color: var(--primary-color, #03a9f4); border: 1px solid var(--divider-color, #e0e0e0); }
    button.danger { background: transparent; color: #c62828; border: 1px solid rgba(198,40,40,.4); }
    button:disabled { opacity: .45; cursor: not-allowed; }
    input[type="text"], input[type="number"], select {
      font: inherit; padding: 7px 9px; border-radius: 8px; color: inherit;
      border: 1px solid var(--divider-color, #e0e0e0); background: var(--card-background-color, #fff);
    }
    input[type="range"] { width: 100%; }
    .editor { display: grid; grid-template-columns: minmax(0,1fr) 340px; gap: 16px; margin-top: 12px; }
    @media (max-width: 1100px) { .editor { grid-template-columns: minmax(0,1fr); } }
    .panel {
      background: var(--card-background-color, #fff); border-radius: 12px; padding: 14px;
      box-shadow: 0 1px 3px rgba(0,0,0,.12);
    }
    .panel h3 { margin: 0 0 10px; font-size: 15px; font-weight: 500; }
    .stage { position: relative; width: 100%; aspect-ratio: 16 / 9; background: #000; border-radius: 10px; overflow: hidden; }
    .stage img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: contain; display: block; }
    .stage canvas { position: absolute; inset: 0; width: 100%; height: 100%; cursor: crosshair; }
    .stage .badge {
      position: absolute; left: 10px; top: 10px; padding: 3px 10px; border-radius: 999px;
      background: rgba(0,0,0,.55); color: #fff; font-size: 12px; pointer-events: none;
    }
    .toolbar { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin: 10px 0; }
    .toolbar label { color: var(--secondary-text-color, #727272); font-size: 12px; }
    .hint { color: var(--secondary-text-color, #727272); font-size: 12px; line-height: 1.5; }
    .row { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
    .zone {
      display: flex; align-items: center; gap: 8px; padding: 8px; border-radius: 8px;
      border: 1px solid var(--divider-color, #e0e0e0); margin-bottom: 6px; cursor: pointer;
    }
    .zone.sel { border-color: var(--primary-color, #03a9f4); background: rgba(3,169,244,.08); }
    .zone .swatch { width: 12px; height: 12px; border-radius: 3px; flex: 0 0 auto; }
    .zone .nm { flex: 1 1 auto; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .zone .meta { color: var(--secondary-text-color, #727272); font-size: 12px; }
    .stat { display: flex; justify-content: space-between; gap: 8px; padding: 4px 0; border-bottom: 1px solid var(--divider-color, #eee); }
    .stat span:first-child { color: var(--secondary-text-color, #727272); }
    .slider { margin-bottom: 10px; }
    .slider .top { display: flex; justify-content: space-between; font-size: 12px; color: var(--secondary-text-color, #727272); }
    .events { display: flex; flex-direction: column; gap: 8px; max-height: 320px; overflow: auto; }
    .ev { display: flex; gap: 10px; align-items: center; border-bottom: 1px solid var(--divider-color, #eee); padding-bottom: 8px; }
    .ev img { width: 96px; height: 54px; object-fit: cover; border-radius: 6px; background: #222; flex: 0 0 auto; }
    .ev .when { font-size: 12px; color: var(--secondary-text-color, #727272); }
    .switch { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-bottom: 10px; }
    .switch .txt { flex: 1 1 auto; }
    .switch .txt b { display: block; font-weight: 500; }
    code { background: var(--secondary-background-color, #eee); padding: 1px 5px; border-radius: 4px; word-break: break-all; }
    .overlay {
      position: fixed; inset: 0; background: rgba(0,0,0,.45); z-index: 60;
      display: flex; align-items: center; justify-content: center; padding: 16px;
    }
    .modal {
      width: 100%; max-width: 420px; background: var(--card-background-color, #fff);
      border-radius: 14px; padding: 20px; box-shadow: 0 8px 30px rgba(0,0,0,.35);
      color: var(--primary-text-color, #212121);
    }
    .modal h2 { margin: 0 0 14px; font-size: 18px; font-weight: 500; }
    .field { display: block; margin-bottom: 12px; }
    .field span { display: block; font-size: 12px; color: var(--secondary-text-color, #727272); margin-bottom: 4px; }
    .field input[type="text"], .field input[type="number"], .field select { width: 100%; }
    .field input[type="checkbox"] { width: auto; }
    .modal .actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 6px; }
    .error { background: rgba(229,57,53,.12); color: #c62828; border-radius: 8px; padding: 8px 10px; font-size: 13px; margin-bottom: 12px; }
    .card { position: relative; }
    .card .del {
      position: absolute; top: 12px; right: 12px; width: 30px; height: 30px; padding: 0; z-index: 2;
      border-radius: 50%; background: color-mix(in srgb, var(--card-background-color, #fff) 80%, transparent);
      color: var(--secondary-text-color, #727272); border: 1px solid var(--divider-color, #e0e0e0);
      display: flex; align-items: center; justify-content: center; font-size: 14px; line-height: 1;
      backdrop-filter: blur(4px);
    }
    .card .del:hover { background: rgba(229,57,53,.16); color: #c62828; border-color: rgba(229,57,53,.4); }
    .app-card { display: flex; flex-direction: column; gap: 8px; }
    .app-card .app-icon { font-size: 26px; line-height: 1; }
    .app-card .app-actions { margin-top: 4px; }
    .app-card.stopped { opacity: .8; }
    .toast {
      position: fixed; left: 50%; bottom: 28px; transform: translateX(-50%);
      background: #323232; color: #fff; padding: 10px 18px; border-radius: 8px; z-index: 50;
      box-shadow: 0 3px 12px rgba(0,0,0,.3); font-size: 13px;
    }
  `;

  const CAMERA_SVG =
    '<svg viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg"><path d="M3 7.4 11.4 2.5 21 7.8v8.5l-9.4 5.2L3 16.5V7.4m8.4-2.6L5.6 8.2l5.9 3.3L18 7.9l-6.6-3.1M5 9.8v5.6l6.5 3.7v-5.7L5 9.8m8.2 3.4v5.6l5.8-3.3V10l-5.8 3.2M8.3 11a3.1 3.1 0 1 0 0 6.2 3.1 3.1 0 0 0 0-6.2m0 1.5a1.6 1.6 0 1 1 0 3.2 1.6 1.6 0 0 1 0-3.2"/></svg>';

  const h = (tag, props, ...children) => {
    const node = document.createElement(tag);
    Object.entries(props || {}).forEach(([key, value]) => {
      if (value === null || value === undefined || value === false) return;
      if (key === "class") node.className = value;
      else if (key === "style" && typeof value === "object") Object.assign(node.style, value);
      else if (key.startsWith("on") && typeof value === "function") node.addEventListener(key.slice(2), value);
      else if (key === "html") node.innerHTML = value;
      else node.setAttribute(key, value);
    });
    children.flat(Infinity).forEach((child) => {
      if (child === null || child === undefined || child === false) return;
      node.appendChild(typeof child === "object" ? child : document.createTextNode(String(child)));
    });
    return node;
  };

  class RecameraMotionPanel extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: "open" });
      this._devices = [];
      this._state = null;
      this._zones = [];
      this._draft = [];
      this._draftType = "include";
      this._draftName = "";
      this._selected = null;
      this._dirty = false;
      this._settings = {};
      this._pollTimer = null;
      this._streamTimer = null;
      this._toastTimer = null;
      this._pointer = null;
      this._token = "";
      this._loadError = "";
      this._addFlow = null;
      this._addModalEl = null;
      this._addError = "";
      this._view = "home";
      this._previewImg = null;
      this._previewTimer = null;
      this._homeTimer = null;
      this._selectedApp = null;
      try {
        const savedLanguage = window.localStorage.getItem("recamera-language");
        this._langChoice = savedLanguage === "zh" || savedLanguage === "en" ? savedLanguage : null;
      } catch (_) {
        this._langChoice = null;
      }
      this._lang = this._langChoice || "en";
    }

    connectedCallback() {
      if (!this._built) this._build();
      if (this._hass && !this._booted) this._boot();
      else if (this._booted) this._startHomeTimer();
    }

    disconnectedCallback() {
      this._stopTimers();
      if (this._homeTimer) clearInterval(this._homeTimer);
      this._homeTimer = null;
    }

    set hass(value) {
      if (!value) return;
      const tokenChanged = this._token !== value.auth?.accessToken;
      this._hass = value;
      const nextLanguage = this._langChoice ||
        (String(value.language || "en").toLowerCase().startsWith("zh") ? "zh" : "en");
      const languageChanged = this._lang !== nextLanguage;
      this._lang = nextLanguage;
      if (!this._built && this.isConnected) this._build();
      if (!this._booted && this._built) this._boot();
      if (languageChanged && this._built) {
        this._updateLanguageSwitch();
        if (this._booted) this._render();
      }
      if (tokenChanged && this._state) {
        if (this._view === "app" && this._img) this._startStream();
        else if (this._view === "device" && this._previewImg) this._startPreview();
      }
    }

    t(key) {
      return (TEXT[this._lang] || TEXT.en)[key] || TEXT.en[key] || key;
    }

    _appName(app) {
      if (app.id === "region_motion") return this.t("app_region_motion");
      return app.name || (this.t(app.name_key) !== app.name_key ? this.t(app.name_key) : app.id);
    }

    _appDescription(app) {
      if (app.id === "region_motion") return this.t("app_region_motion_desc");
      return app.description || (this.t(app.description_key) !== app.description_key ? this.t(app.description_key) : "");
    }

    _setLanguage(language) {
      if (language !== "zh" && language !== "en") return;
      this._langChoice = language;
      this._lang = language;
      try { window.localStorage.setItem("recamera-language", language); } catch (_) { /* Private browsing. */ }
      this._updateLanguageSwitch();
      this._render();
    }

    _updateLanguageSwitch() {
      this._languageSwitch?.querySelectorAll("button").forEach((button) => {
        const active = button.dataset.lang === this._lang;
        button.classList.toggle("active", active);
        button.setAttribute("aria-pressed", String(active));
      });
    }

    // ---------------------------------------------------------------- shell
    _build() {
      this._built = true;
      const style = document.createElement("style");
      style.textContent = STYLE;
      this._root = h("div", { class: "wrap" });
      this._languageSwitch = h("div", { class: "global-language lang-switch", role: "group", "aria-label": "Language / 语言" },
        h("button", { type: "button", "data-lang": "zh", onclick: () => this._setLanguage("zh") }, "中"),
        h("button", { type: "button", "data-lang": "en", onclick: () => this._setLanguage("en") }, "EN"));
      this.shadowRoot.replaceChildren(style, this._root, this._languageSwitch);
      this._updateLanguageSwitch();
      this._root.appendChild(h("div", { class: "view" }, this.t("loading")));
    }

    async _boot() {
      if (this._booted) return;
      this._booted = true;
      await this._loadDevices();
      this._startHomeTimer();
    }

    _startHomeTimer() {
      if (this._homeTimer) return;
      this._homeTimer = setInterval(() => {
        if (this._view === "home") this._loadDevices();
      }, 10000);
    }

    async ws(type, data = {}) {
      return this._hass.callWS({ type: `recamera/${type}`, ...data });
    }

    toast(message, kind = "ok") {
      if (this._toastTimer) clearTimeout(this._toastTimer);
      this.shadowRoot.querySelectorAll(".toast").forEach((node) => node.remove());
      const node = h("div", { class: "toast" }, message);
      if (kind === "bad") node.style.background = "#c62828";
      this.shadowRoot.appendChild(node);
      this._toastTimer = setTimeout(() => node.remove(), 3200);
    }

    // ----------------------------------------------------------------- home
    async _loadDevices() {
      try {
        const result = await this.ws("devices");
        this._devices = result.devices || [];
        this._loadError = "";
      } catch (error) {
        this._devices = [];
        // Surface the reason inline: an empty list alone reads as "no camera
        // configured", which hides real failures such as a missing command.
        this._loadError = String(error?.message || error);
        this.toast(this._loadError, "bad");
      }
      if (this._state) {
        const still = this._devices.find((device) => device.entry_id === this._state.entry_id);
        if (!still) {
          this._state = null;
          this._view = "home";
          this._stopTimers();
        }
      }
      this._render();
    }

    _render() {
      if (!this._built) return;
      let view;
      if (this._view === "custom_app" && this._state) view = this._customAppView();
      else if (this._view === "app" && this._state) view = this._editorView();
      else if (this._view === "device" && this._state) view = this._deviceView();
      else view = this._homeView();
      this._root.replaceChildren(h("div", { class: "view" }, view));
      this._stopPolling();
      if (this._streamTimer) {
        clearTimeout(this._streamTimer);
        this._streamTimer = null;
      }
      this._resizeObserver?.disconnect();
      this._stopPreview();
      if (this._view === "app" && this._state) {
        this._startStream();
        this._applyState();
        this._startPolling();
      } else if (this._view === "device" && this._state) {
        this._startPreview();
      }
    }

    _homeView() {
      const header = h(
        "div",
        { class: "header" },
        h("h1", {}, this.t("title")),
        h("span", { class: "sub" }, this.t("subtitle")),
        h("span", { class: "spacer" }),
        h("button", { onclick: () => this._openAddDevice() }, this.t("add_device")),
        h(
          "button",
          {
            class: "ghost",
            onclick: () => {
              history.pushState(null, "", "/config/integrations");
              window.dispatchEvent(new Event("location-changed"));
            },
          },
          this.t("add_integration")
        ),
        h("button", { class: "ghost", onclick: () => this._loadDevices() }, this.t("refresh"))
      );

      if (!this._devices.length) {
        return h(
          "div",
          {},
          header,
          this._loadError
            ? h(
                "div",
                { class: "empty" },
                h("div", {}, this.t("load_failed")),
                h("div", { class: "hint", style: { color: "#c62828" } }, this._loadError),
                h("button", { class: "ghost", onclick: () => this._loadDevices() }, this.t("retry"))
              )
            : h(
                "div",
                { class: "empty" },
                h("div", {}, this.t("no_devices")),
                h("div", { class: "hint" }, this.t("no_devices_hint")),
                h("button", { style: { marginTop: "14px" }, onclick: () => this._openAddDevice() }, this.t("add_device"))
              )
        );
      }

      const cards = this._devices.map((device) => this._deviceCard(device));
      return h("div", {}, header, h("div", { class: "cards" }, cards));
    }

    _deviceCard(device) {
      const running = (device.apps || []).find((app) => app.running);
      const runningLabel = running ? this._appName(running) : null;
      const chips = [
        h(
          "span",
          { class: "chip" },
          h("i", { class: `dot ${device.available ? "ok" : "bad"}` }),
          device.available ? this.t("online") : this.t("offline")
        ),
        h("span", { class: "chip" },
          h("i", { class: `dot ${device.reachable ? "ok" : "bad"}` }),
          device.reachable ? this.t("reachable") : this.t("unreachable")),
        running
          ? h("span", { class: "chip" }, h("i", { class: "dot ok" }), runningLabel)
          : h("span", { class: "chip" }, h("i", { class: "dot" }), this.t("app_stopped")),
        running?.id === "region_motion"
          ? h("span", { class: "chip" }, device.enabled ? this.t("detection_on") : this.t("detection_off"))
          : null,
      ];
      if (device.legacy_device) chips.push(h("span", { class: "chip warn" }, "legacy"));

      return h(
        "div",
        { class: "card device-card", onclick: () => this._openDevice(device.entry_id) },
        h(
          "button",
          {
            class: "del",
            title: this.t("delete_device"),
            onclick: (event) => {
              event.stopPropagation();
              this._deleteDevice(device.entry_id);
            },
          },
          "✕"
        ),
        h("div", { class: "device-visual" }, h("div", { class: "camera-mark", html: CAMERA_SVG })),
        h(
          "div",
          { class: "device-body" },
          h("div", { class: "name" }, device.name),
          h("div", { class: "host" }, `${device.host}:${device.api_port}`),
          h("div", { class: "meta" }, `${this.t("running_app")}: ${runningLabel || this.t("app_stopped")}${running?.version ? ` · v${running.version}` : ""}`),
          h("div", { class: "chip-row" }, chips)
        )
      );
    }

    _stillToken(entityId) {
      const state = this._hass?.states?.[entityId];
      return state?.attributes?.access_token || "";
    }

    // ------------------------------------------------- multi-device manage
    _flowError(errors) {
      const key = errors?.base || Object.values(errors || {})[0];
      if (!key) return "";
      const mapped = this.t(`err_${key}`);
      return mapped !== `err_${key}` ? mapped : key;
    }

    _abortReason(reason) {
      if (!reason) return this.t("err_unknown");
      const key = `err_${reason}`;
      const mapped = this.t(key);
      return mapped !== key ? mapped : reason;
    }

    _apiErrorText(error) {
      const candidates = [error?.body?.message, error?.message, error?.body?.error];
      const message = candidates.find((value) => typeof value === "string" && value.trim());
      return message || (error?.status ? `HTTP ${error.status}` : this.t("err_unknown"));
    }

    async _openAddDevice() {
      this._addError = "";
      try {
        this._addFlow = await this._hass.callApi("POST", "config/config_entries/flow", {
          handler: "recamera",
          show_advanced_options: false,
        });
        this._renderAddModal();
      } catch (error) {
        this.toast(this._apiErrorText(error), "bad");
      }
    }

    _schemaField(field) {
      const name = field.name;
      const labelKey = `field_${name}`;
      const label = this.t(labelKey) !== labelKey ? this.t(labelKey) : name;
      const suffix = field.required ? " *" : "";
      let input;
      if (field.type === "boolean") {
        input = h("input", { type: "checkbox", name, ...(field.default ? { checked: "true" } : {}) });
      } else if (field.type === "integer" || field.type === "float") {
        input = h("input", {
          type: "number",
          name,
          value: field.default ?? "",
          ...(field.valueMin != null ? { min: String(field.valueMin) } : {}),
          ...(field.valueMax != null ? { max: String(field.valueMax) } : {}),
        });
      } else if (field.type === "select") {
        input = h(
          "select",
          { name },
          (field.options || []).map((option) => {
            const value = typeof option === "object" ? option.value : option;
            const text = typeof option === "object" ? option.label : option;
            return h("option", { value: String(value) }, text);
          })
        );
      } else {
        input = h("input", { type: "text", name, value: field.default ?? "" });
      }
      return h("label", { class: "field" }, h("span", {}, label + suffix), input);
    }

    _renderAddModal() {
      this._closeAddModal();
      const flow = this._addFlow;
      const errText = this._addError || this._flowError(flow.errors || {});
      const fields = (flow.data_schema || []).map((field) => this._schemaField(field));
      const overlay = h(
        "div",
        { class: "overlay" },
        h(
          "div",
          { class: "modal" },
          h("h2", {}, this.t("add_device_title")),
          errText ? h("div", { class: "error" }, errText) : null,
          h(
            "form",
            {
              onsubmit: (event) => {
                event.preventDefault();
                this._submitAddDevice();
              },
            },
            fields,
            h(
              "div",
              { class: "actions" },
              h("button", { type: "button", class: "ghost", onclick: () => this._cancelAdd() }, this.t("cancel")),
              h("button", { type: "submit" }, this.t("connect_add"))
            )
          )
        )
      );
      this._addModalEl = overlay;
      this.shadowRoot.appendChild(overlay);
    }

    async _submitAddDevice() {
      const form = this._addModalEl.querySelector("form");
      const userInput = {};
      form.querySelectorAll("[name]").forEach((element) => {
        if (element.type === "checkbox") userInput[element.name] = element.checked;
        else if (element.type === "number") {
          if (element.value !== "") userInput[element.name] = Number(element.value);
        } else if (element.value !== "") userInput[element.name] = element.value;
      });
      const button = form.querySelector('[type="submit"]');
      button.disabled = true;
      button.textContent = this.t("connecting");
      this._addError = "";
      try {
        const result = await this._hass.callApi(
          "POST",
          `config/config_entries/flow/${this._addFlow.flow_id}`,
          userInput
        );
        if (result.type === "create_entry") {
          this._closeAddModal();
          this.toast(this.t("device_added"));
          setTimeout(() => this._loadDevices(), 1200);
        } else if (result.type === "abort") {
          // The flow finished (e.g. already_configured). Show the reason and
          // start a fresh flow so the user can correct the input and retry.
          this._addError = this._abortReason(result.reason);
          try {
            this._addFlow = await this._hass.callApi("POST", "config/config_entries/flow", {
              handler: "recamera",
              show_advanced_options: false,
            });
          } catch {
            // keep the finished flow; the error is still shown
          }
          this._renderAddModal();
        } else {
          this._addFlow = result;
          this._renderAddModal();
        }
      } catch (error) {
        this._addError = this._apiErrorText(error);
        this._renderAddModal();
      }
    }

    _closeAddModal() {
      if (this._addModalEl) {
        this._addModalEl.remove();
        this._addModalEl = null;
      }
    }

    _cancelAdd() {
      const flowId = this._addFlow?.flow_id;
      this._closeAddModal();
      if (flowId) {
        this._hass.callApi("DELETE", `config/config_entries/flow/${flowId}`).catch(() => {});
      }
    }

    async _deleteDevice(entryId) {
      if (!window.confirm(this.t("delete_device_confirm"))) return;
      try {
        await this._hass.callApi("DELETE", `config/config_entries/entry/${entryId}`);
        this.toast(this.t("device_removed"));
        if (this._state && this._state.entry_id === entryId) this._state = null;
        this._loadDevices();
      } catch (error) {
        this.toast(String(error?.body?.message || error?.message || error), "bad");
      }
    }

    async _openDevice(entryId) {
      this._root.replaceChildren(h("div", { class: "view" }, this.t("loading")));
      try {
        this._state = await this.ws("state", { entry_id: entryId });
      } catch (error) {
        this.toast(String(error?.message || error), "bad");
        this._state = null;
        this._view = "home";
        this._render();
        return;
      }
      this._view = "device";
      this._render();
    }

    _openApp() {
      this._adoptDeviceState();
      this._view = "app";
      this._render();
    }

    _adoptDeviceState() {
      const config = this._state?.config || {};
      this._settings = {
        pixel_threshold: config.pixel_threshold ?? 20,
        min_motion_pixels: config.min_motion_pixels ?? 120,
        min_blob_pixels: config.min_blob_pixels ?? 40,
        trigger_frames: config.trigger_frames ?? 3,
        clear_frames: config.clear_frames ?? 5,
        warmup_frames: config.warmup_frames ?? 20,
        background_alpha: config.background_alpha ?? 0.04,
        foreground_alpha: config.foreground_alpha ?? 0.002,
      };
      this._zones = (config.zones || []).map((zone, index) => ({
        id: zone.id || `zone-${index + 1}`,
        name: zone.name || zone.id || `zone-${index + 1}`,
        type: zone.type === "exclude" ? "exclude" : "include",
        points: (zone.points || []).map((point) => [Number(point[0]), Number(point[1])]),
      }));
      this._draft = [];
      this._selected = null;
      this._dirty = false;
    }

    // ---------------------------------------------------------- device view
    _runningAppLine(device) {
      const running = (device.apps || []).find((app) => app.running);
      if (!running) return h("div", { class: "hint", style: { marginTop: "6px" } }, this.t("app_stopped"));
      const label = this._appName(running);
      return h("div", { class: "hint", style: { marginTop: "6px" } }, `${this.t("running_app")}: ${label}`);
    }

    _deviceView() {
      const state = this._state;
      const apps = state.apps || [];
      const hasMotionApp = apps.some((app) => app.id === "region_motion");
      const motionRunning = apps.some((app) => app.id === "region_motion" && app.running);
      const chips = [
        h(
          "span",
          { class: "chip" },
          h("i", { class: `dot ${state.available ? "ok" : "bad"}` }),
          state.available ? this.t("online") : this.t("offline")
        ),
        h("span", { class: "chip" },
          h("i", { class: `dot ${state.reachable ? "ok" : "bad"}` }),
          state.reachable ? this.t("reachable") : this.t("unreachable")),
        hasMotionApp ? (motionRunning
          ? (state.motion ? h("span", { class: "chip live" }, this.t("motion")) : h("span", { class: "chip" }, this.t("idle")))
          : h("span", { class: "chip warn" }, this.t("api_unavailable"))) : null,
      ];
      const header = h(
        "div",
        { class: "header" },
        h("button", { class: "ghost", onclick: () => this._backHome() }, `‹ ${this.t("back")}`),
        h("h1", {}, state.name),
        h("span", { class: "sub" }, `${state.host}:${state.api_port}`),
        h("span", { class: "spacer" }),
        h("button", { class: "ghost", onclick: () => this._openDevice(state.entry_id) }, this.t("refresh"))
      );
      return h(
        "div",
        {},
        header,
        h("div", { class: "chip-row", style: { marginTop: "10px" } }, chips),
        hasMotionApp ? h(
          "div",
          { class: "panel", style: { marginTop: "16px" } },
          h("h3", {}, this.t("live")),
          motionRunning
            ? h("div", { class: "preview-stage" },
                (this._previewImg = h("img", { alt: state.name, onerror: () => this._onPreviewError() })))
            : h("div", { class: "empty" }, this.t("api_unavailable")),
          motionRunning
            ? h("div", { class: "hint", style: { marginTop: "8px" } }, this.t("stream_hint"))
            : null
        ) : null,
        h("h3", { style: { margin: "18px 0 4px", fontSize: "15px", fontWeight: "500" } }, this.t("apps_title")),
        h("div", { class: "hint", style: { marginBottom: "10px" } }, this.t("one_app_hint")),
        apps.length ? h("div", { class: "cards" }, apps.map((app) => this._appCard(app)))
          : h("div", { class: "empty" }, this.t("no_apps")),
        h("div", { class: "panel", style: { marginTop: "18px" } },
          h("button", { onclick: () => this._openRepositoryModal() }, this.t("add_repository")),
          h("div", { class: "hint", style: { marginTop: "8px" } }, this.t("repository_hint"))),
        h("div", { class: "panel", style: { marginTop: "18px" } },
          h("button", { onclick: () => this._choosePackage() }, this.t("upload_package")),
          h("div", { class: "hint", style: { marginTop: "8px" } }, this.t("upload_hint")))
      );
    }

    _openRepositoryModal() {
      const input = h("input", { type: "text", name: "repository", placeholder: "https://github.com/owner/repo", required: "true" });
      const errorBox = h("div", { class: "error", style: { display: "none" } });
      const overlay = h("div", { class: "overlay" },
        h("div", { class: "modal" },
          h("h2", {}, this.t("add_repository")),
          errorBox,
          h("form", { onsubmit: async (event) => {
            event.preventDefault();
            const button = event.target.querySelector('button[type="submit"]');
            button.disabled = true;
            try {
              await this.ws("add_repository", { entry_id: this._state.entry_id, url: input.value.trim() });
              overlay.remove();
              this._state = await this.ws("state", { entry_id: this._state.entry_id });
              this._render();
              this.toast(this.t("repository_added"));
            } catch (error) {
              errorBox.textContent = this._apiErrorText(error);
              errorBox.style.display = "block";
            } finally {
              button.disabled = false;
            }
          } },
            h("label", { class: "field" }, h("span", {}, this.t("repository_url")), input),
            h("div", { class: "actions" },
              h("button", { type: "button", class: "ghost", onclick: () => overlay.remove() }, this.t("cancel")),
              h("button", { type: "submit" }, this.t("add_repository"))))));
      this.shadowRoot.appendChild(overlay);
      input.focus();
    }

    _choosePackage() {
      const input = h("input", { type: "file", accept: ".zip,application/zip" });
      input.style.display = "none";
      this.shadowRoot.appendChild(input);
      input.addEventListener("change", async () => {
        const file = input.files?.[0];
        input.remove();
        if (!file) return;
        if (file.size > 8 * 1024 * 1024) {
          this.toast(this.t("package_too_large"), "bad");
          return;
        }
        try {
          const bytes = new Uint8Array(await file.arrayBuffer());
          let binary = "";
          for (let i = 0; i < bytes.length; i += 32768) {
            binary += String.fromCharCode(...bytes.subarray(i, i + 32768));
          }
          await this.ws("upload_package", {
            entry_id: this._state.entry_id,
            package: btoa(binary),
          });
          this._state = await this.ws("state", { entry_id: this._state.entry_id });
          this._render();
          this.toast(this.t("package_uploaded"));
        } catch (error) {
          this.toast(String(error?.message || error), "bad");
        }
      });
      input.addEventListener("cancel", () => input.remove(), { once: true });
      input.click();
    }

    _customAppView() {
      const app = (this._state.apps || []).find((item) => item.id === this._selectedApp);
      if (!app) return this._deviceView();
      const events = (this._state.events || []).filter((item) => item.source === app.source);
      return h("div", {},
        h("div", { class: "header" },
          h("button", { class: "ghost", onclick: () => this._closeDevice() }, `‹ ${this.t("back")}`),
          h("h1", {}, app.name), h("span", { class: "spacer" }),
          h("button", { class: "ghost", onclick: () => this._openDevice(this._state.entry_id) }, this.t("refresh"))),
        h("div", { class: "panel" },
          h("div", { class: "hint" }, `${this.t("running_app")}: ${app.running ? this.t("app_running") : this.t("waiting_app")}`),
          h("div", { class: "hint" }, `${this.t("push_url")}: `, h("code", {}, this._state.push_url || "—")),
          h("h3", { style: { marginTop: "18px" } }, this.t("custom_events")),
          events.length ? events.map((event) => h("div", { class: "zone" },
            h("span", {}, event.event), h("span", { class: "spacer" }),
            h("span", { class: "hint" }, event.timestamp)))
            : h("div", { class: "hint" }, this.t("no_events"))));
    }

    _startPreview() {
      if (this._previewTimer) {
        clearTimeout(this._previewTimer);
        this._previewTimer = null;
      }
      const entities = this._state?.entities || {};
      const camera = entities.camera;
      if (!this._previewImg) return;
      if (!camera) {
        this._previewImg.removeAttribute("src");
        return;
      }
      const token = this._stillToken(camera);
      this._previewImg.src = `/api/camera_proxy_stream/${camera}${token ? `?token=${token}` : ""}`;
    }

    _onPreviewError() {
      if (this._previewTimer) clearTimeout(this._previewTimer);
      this._previewTimer = setTimeout(() => this._startPreview(), 4000);
    }

    _stopPreview() {
      if (this._previewTimer) {
        clearTimeout(this._previewTimer);
        this._previewTimer = null;
      }
      if (this._previewImg) this._previewImg.removeAttribute("src");
    }

    _appCard(app) {
      const label = this._appName(app);
      const desc = this._appDescription(app);
      const running = app.running;
      const open = () => {
        if (app.id === "region_motion") {
          if (running) this._openApp();
          else this.toast(this.t("api_unavailable"), "bad");
        }
        else { this._selectedApp = app.id; this._view = "custom_app"; this._render(); }
      };
      return h(
        "div",
        { class: `card app-card${running ? "" : " stopped"}`, onclick: open },
        h("button", { class: "del", title: this.t("remove_app"), onclick: async (event) => {
          event.stopPropagation();
          if (!window.confirm(this.t("remove_app_confirm"))) return;
          try {
            await this.ws("remove_app", { entry_id: this._state.entry_id, app_id: app.id });
            this._state = await this.ws("state", { entry_id: this._state.entry_id });
            this._render();
          } catch (error) { this.toast(this._apiErrorText(error), "bad"); }
        } }, "✕"),
        h("div", { class: "app-icon" }, "▦"),
        h("h2", {}, label),
        desc ? h("div", { class: "hint" }, desc) : null,
        h("div", { class: "chips" }, h("span", { class: `chip ${running ? "ok" : ""}` },
          running ? this.t("app_running") : app.uploaded ? this.t("uploaded") : this.t("app_stopped"))),
        h(
          "div",
          { class: "app-actions" },
          running || app.uploaded
            ? h("button", { onclick: (event) => { event.stopPropagation(); open(); } }, this.t("open_app"))
            : h("span", { class: "hint" }, this.t("waiting_app"))
        )
      );
    }

    // --------------------------------------------------------------- editor
    _editorView() {
      const state = this._state;
      const entities = state.entities || {};

      this._img = h("img", { alt: state.name, onerror: () => this._onStreamError(), onload: () => this._drawOverlay() });
      this._canvas = h("canvas", {
        onclick: (event) => this._onCanvasClick(event),
        oncontextmenu: (event) => {
          event.preventDefault();
          this._undoPoint();
        },
        onmousemove: (event) => {
          this._pointer = this._toNormalized(event);
          this._drawOverlay();
        },
        onmouseleave: () => {
          this._pointer = null;
          this._drawOverlay();
        },
      });
      this._stage = h(
        "div",
        { class: "stage" },
        this._img,
        this._canvas,
        (this._badge = h("span", { class: "badge" }, this.t("live")))
      );

      this._resizeObserver?.disconnect();
      this._resizeObserver = new ResizeObserver(() => this._drawOverlay());
      this._resizeObserver.observe(this._stage);

      const header = h(
        "div",
        { class: "header" },
        h("button", { class: "ghost", onclick: () => this._closeDevice() }, `‹ ${this.t("back")}`),
        h("h1", {}, this.t("card_title")),
        h("span", { class: "sub" }, `${state.name} · ${state.host}`),
        h("span", { class: "spacer" }),
        (this._dirtyChip = h("span", { class: "chip warn", style: { display: "none" } }, this.t("dirty_hint"))),
        (this._statusChips = h("div", { class: "chips" })),
        h("button", { class: "ghost", onclick: () => this._refreshDevice() }, this.t("refresh")),
        h(
          "button",
          {
            class: "ghost",
            onclick: () => this._setEnabled(!this._state.enabled),
          },
          state.enabled ? this.t("disable") : this.t("enable")
        ),
        (this._saveButton = h("button", { onclick: () => this._save() }, this.t("save")))
      );

      const left = h(
        "div",
        {},
        h("div", { class: "panel" }, h("h3", {}, this.t("live")), this._stage, h("div", { class: "hint", style: { marginTop: "8px" } }, this.t("stream_hint"))),
        h(
          "div",
          { class: "panel", style: { marginTop: "16px" } },
          h("h3", {}, this.t("tools")),
          h(
            "div",
            { class: "toolbar" },
            h(
              "select",
              {
                onchange: (event) => {
                  this._draftType = event.target.value;
                },
              },
              h("option", { value: "include", selected: this._draftType === "include" }, this.t("type_include")),
              h("option", { value: "exclude", selected: this._draftType === "exclude" }, this.t("type_exclude"))
            ),
            (this._nameInput = h("input", {
              type: "text",
              placeholder: this.t("zone_name_ph"),
              value: this._draftName,
              oninput: (event) => {
                this._draftName = event.target.value;
              },
            })),
            h("button", { onclick: () => this._finishPolygon() }, this.t("finish")),
            h("button", { class: "ghost", onclick: () => this._undoPoint() }, this.t("undo")),
            h(
              "button",
              {
                class: "ghost",
                onclick: () => {
                  this._draft = [];
                  this._drawOverlay();
                },
              },
              this.t("clear_draft")
            ),
            h("button", { class: "ghost", onclick: () => this._resetBackground() }, this.t("reset_background"))
          ),
          h("div", { class: "hint" }, this.t("draw_hint")),
          h("div", { class: "row", style: { marginTop: "12px" } }, h("label", {}, this.t("preview_fps")), (this._fpsInput = h("input", {
            type: "range",
            min: "1",
            max: "20",
            step: "1",
            value: String(state.preview_fps || 8),
            oninput: (event) => {
              this._fpsLabel.textContent = `${event.target.value} fps`;
            },
            onchange: (event) => this._setPreviewFps(Number(event.target.value)),
          })), (this._fpsLabel = h("span", { class: "meta" }, `${state.preview_fps || 8} fps`)))
        ),
        h("div", { class: "panel", style: { marginTop: "16px" } }, h("h3", {}, this.t("zones")), (this._zoneList = h("div", {})))
      );

      const right = h(
        "div",
        {},
        h("div", { class: "panel" }, h("h3", {}, this.t("stats")), (this._stats = h("div", {}))),
        h("div", { class: "panel", style: { marginTop: "16px" } }, h("h3", {}, this.t("sensitivity")), this._sensitivityControls()),
        h("div", { class: "panel", style: { marginTop: "16px" } }, h("h3", {}, this.t("notify")), this._notifyControls()),
        h("div", { class: "panel", style: { marginTop: "16px" } }, h("h3", {}, this.t("events")), (this._events = h("div", { class: "events" })))
      );

      return h("div", {}, header, h("div", { class: "editor" }, left, right));
    }

    _sensitivityControls() {
      const defs = [
        ["pixel_threshold", 1, 120, 1],
        ["min_motion_pixels", 1, 5000, 1],
        ["min_blob_pixels", 1, 2000, 1],
        ["trigger_frames", 1, 30, 1],
        ["clear_frames", 1, 60, 1],
        ["warmup_frames", 0, 200, 1],
      ];
      this._sliders = {};
      const nodes = defs.map(([key, min, max, step]) => {
        const label = h("span", {}, String(this._settings[key]));
        const input = h("input", {
          type: "range",
          min: String(min),
          max: String(max),
          step: String(step),
          value: String(this._settings[key]),
          oninput: (event) => {
            this._settings[key] = Number(event.target.value);
            label.textContent = event.target.value;
            this._markDirty();
          },
        });
        this._sliders[key] = { input, label };
        return h("div", { class: "slider" }, h("div", { class: "top" }, h("span", {}, this.t(key)), label), input);
      });

      const alpha = (key, min, max, step) => {
        const label = h("span", {}, String(this._settings[key]));
        const input = h("input", {
          type: "range",
          min: String(min),
          max: String(max),
          step: String(step),
          value: String(this._settings[key]),
          oninput: (event) => {
            this._settings[key] = Number(event.target.value);
            label.textContent = event.target.value;
            this._markDirty();
          },
        });
        this._sliders[key] = { input, label };
        return h("div", { class: "slider" }, h("div", { class: "top" }, h("span", {}, this.t(key)), label), input);
      };
      nodes.push(alpha("background_alpha", 0.005, 0.5, 0.005));
      nodes.push(alpha("foreground_alpha", 0, 0.05, 0.001));
      nodes.push(h("div", { class: "hint" }, this.t("automation_hint")));
      return h("div", {}, nodes);
    }

    _notifyControls() {
      const state = this._state;
      this._haSwitch = h("input", {
        type: "checkbox",
        checked: state.ha_notification ? "checked" : null,
        onchange: (event) => this._setNotify({ ha_notification: event.target.checked }),
      });
      this._pushSwitch = h("input", {
        type: "checkbox",
        checked: state.push_enabled ? "checked" : null,
        onchange: (event) => this._setNotify({ push_enabled: event.target.checked }),
      });
      this._pushInfo = h("div", { class: "hint" });
      return h(
        "div",
        {},
        h(
          "div",
          { class: "switch" },
          h("div", { class: "txt" }, h("b", {}, this.t("ha_notification")), h("span", { class: "hint" }, this.t("ha_notification_hint"))),
          this._haSwitch
        ),
        h(
          "div",
          { class: "switch" },
          h("div", { class: "txt" }, h("b", {}, this.t("device_push")), h("span", { class: "hint" }, this.t("device_push_hint"))),
          this._pushSwitch
        ),
        this._pushInfo,
        h(
          "div",
          { class: "toolbar" },
          h("button", { class: "ghost", onclick: () => this._testPush() }, this.t("test_push"))
        )
      );
    }

    // --------------------------------------------------------------- stream
    _startStream() {
      if (this._streamTimer) {
        clearTimeout(this._streamTimer);
        this._streamTimer = null;
      }
      const entities = this._state?.entities || {};
      const camera = entities.camera;
      if (!this._img) return;
      if (!camera) {
        this._img.removeAttribute("src");
        return;
      }
      const token = this._stillToken(camera);
      this._img.src = `/api/camera_proxy_stream/${camera}${token ? `?token=${token}` : ""}`;
    }

    _onStreamError() {
      if (this._badge) this._badge.textContent = this.t("stream_error");
      if (this._streamTimer) clearTimeout(this._streamTimer);
      this._streamTimer = setTimeout(() => this._startStream(), 4000);
    }

    _startPolling() {
      this._stopPolling();
      this._pollTimer = setInterval(() => this._poll(), POLL_MS);
    }

    _stopPolling() {
      if (this._pollTimer) clearInterval(this._pollTimer);
      this._pollTimer = null;
    }

    _stopTimers() {
      this._stopPolling();
      if (this._streamTimer) clearTimeout(this._streamTimer);
      this._streamTimer = null;
      this._resizeObserver?.disconnect();
      this._stopPreview();
    }

    async _poll() {
      if (!this._state) return;
      try {
        const state = await this.ws("state", { entry_id: this._state.entry_id });
        const keep = { zones: this._zones, draft: this._draft, dirty: this._dirty };
        this._state = state;
        if (!keep.dirty) {
          this._zones = (state.config?.zones || []).map((zone, index) => ({
            id: zone.id || `zone-${index + 1}`,
            name: zone.name || zone.id || `zone-${index + 1}`,
            type: zone.type === "exclude" ? "exclude" : "include",
            points: (zone.points || []).map((point) => [Number(point[0]), Number(point[1])]),
          }));
          this._selected = null;
        }
        this._applyState();
      } catch (error) {
        // Keep the last good state; the chips already show availability.
      }
    }

    _applyState() {
      const state = this._state;
      if (!state) return;

      if (this._statusChips) {
        const chips = [
          h("span", { class: `chip ${state.available ? "ok" : "bad"}` }, state.available ? this.t("online") : this.t("offline")),
          state.motion ? h("span", { class: "chip live" }, this.t("motion")) : h("span", { class: "chip" }, this.t("idle")),
        ];
        if (state.warming_up) chips.push(h("span", { class: "chip warn" }, this.t("warming")));
        if (!state.configured) chips.push(h("span", { class: "chip warn" }, this.t("zones_none")));
        this._statusChips.replaceChildren(...chips);
      }
      if (this._badge) {
        this._badge.textContent = state.motion ? this.t("motion") : this.t("live");
        this._badge.style.background = state.motion ? "rgba(229,57,53,.85)" : "rgba(0,0,0,.55)";
      }
      if (this._dirtyChip) this._dirtyChip.style.display = this._dirty ? "" : "none";
      this._renderZoneList();
      this._renderStats();
      this._renderEvents();
      this._renderPushInfo();
      this._drawOverlay();
    }

    _renderStats() {
      if (!this._stats) return;
      const status = this._state.status || {};
      const bbox = this._state.bbox;
      const rows = [
        [this.t("stat_motion_pixels"), String(this._state.motion_pixels ?? 0)],
        [this.t("stat_largest_blob"), String(this._state.largest_blob_pixels ?? 0)],
        [this.t("stat_ratio"), `${((this._state.motion_ratio || 0) * 100).toFixed(2)}%`],
        [this.t("stat_mask"), String(status.active_mask_pixels ?? "-")],
        [this.t("stat_frames"), String(status.frame_count ?? "-")],
        [
          this.t("stat_bbox"),
          bbox ? `${bbox.map((value) => Number(value).toFixed(3)).join(", ")}` : "-",
        ],
      ];
      if (this._state.last_error) rows.push([this.t("stat_error"), String(this._state.last_error)]);
      this._stats.replaceChildren(
        ...rows.map(([label, value]) => h("div", { class: "stat" }, h("span", {}, label), h("span", {}, value)))
      );
    }

    _renderPushInfo() {
      if (!this._pushInfo) return;
      const state = this._state;
      const stats = state.notify_state?.stats || {};
      const children = [];
      if (state.push_url) {
        children.push(h("div", { class: "hint" }, `${this.t("push_url")}: `, h("code", {}, state.push_url)));
      } else {
        children.push(h("div", { class: "hint", style: { color: "#b26a00" } }, this.t("push_none")));
      }
      if (state.push_error) {
        children.push(h("div", { class: "hint", style: { color: "#c62828" } }, `${this.t("push_error")}: ${state.push_error}`));
      }
      children.push(
        h(
          "div",
          { class: "hint" },
          `${this.t("push_stats")}: ${stats.sent ?? 0} / ${state.push_received ?? 0}`
        )
      );
      this._pushInfo.replaceChildren(...children);
    }

    _renderZoneList() {
      if (!this._zoneList) return;
      if (!this._zones.length) {
        this._zoneList.replaceChildren(h("div", { class: "hint" }, this.t("no_zones")));
        return;
      }
      this._zoneList.replaceChildren(
        ...this._zones.map((zone, index) =>
          h(
            "div",
            {
              class: `zone ${this._selected === index ? "sel" : ""}`,
              onclick: () => {
                this._selected = this._selected === index ? null : index;
                this._renderZoneList();
                this._drawOverlay();
              },
            },
            h("span", {
              class: "swatch",
              style: { background: zone.type === "exclude" ? "#ffa726" : "#43a047" },
            }),
            h("span", { class: "nm" }, zone.name || zone.id),
            h("span", { class: "meta" }, `${zone.points.length} ${this.t("points")}`),
            h(
              "button",
              {
                class: "danger",
                onclick: (event) => {
                  event.stopPropagation();
                  if (!confirm(this.t("confirm_delete"))) return;
                  this._zones.splice(index, 1);
                  if (this._selected === index) this._selected = null;
                  this._markDirty();
                },
              },
              this.t("delete_zone")
            )
          )
        )
      );
    }

    _renderEvents() {
      if (!this._events) return;
      const events = (this._state.events || []).slice(0, 12);
      if (!events.length) {
        this._events.replaceChildren(h("div", { class: "hint" }, this.t("no_events")));
        return;
      }
      this._events.replaceChildren(
        ...events.map((event) => {
          const when = event.captured_at ? new Date(event.captured_at).toLocaleString() : "-";
          const start = event.event === "motion_start";
          const thumb = event.image_url
            ? h("img", { src: event.image_url, alt: "", loading: "lazy" })
            : h("div", { class: "ev", style: { width: "96px", height: "54px", background: "#222", borderRadius: "6px" } });
          return h(
            "div",
            { class: "ev" },
            thumb,
            h(
              "div",
              {},
              h("div", {}, h("span", { class: `chip ${start ? "live" : ""}` }, start ? this.t("event_start") : this.t("event_end")), ` #${event.event_id}`),
              h("div", { class: "when" }, when),
              h(
                "div",
                { class: "when" },
                `${this.t("stat_motion_pixels")}: ${event.motion_pixels ?? 0} · ${((event.motion_ratio || 0) * 100).toFixed(2)}%`
              )
            )
          );
        })
      );
    }

    // --------------------------------------------------------------- canvas
    _geometry() {
      const img = this._img;
      const stage = this._stage;
      if (!img || !stage) return null;
      const rect = stage.getBoundingClientRect();
      const naturalW = img.naturalWidth || 16;
      const naturalH = img.naturalHeight || 9;
      const scale = Math.min(rect.width / naturalW, rect.height / naturalH);
      const width = naturalW * scale;
      const height = naturalH * scale;
      return {
        rect,
        x: (rect.width - width) / 2,
        y: (rect.height - height) / 2,
        w: width,
        h: height,
      };
    }

    _toNormalized(event) {
      const geo = this._geometry();
      if (!geo || geo.w <= 0 || geo.h <= 0) return null;
      const rect = geo.rect;
      const nx = (event.clientX - rect.left - geo.x) / geo.w;
      const ny = (event.clientY - rect.top - geo.y) / geo.h;
      if (nx < 0 || nx > 1 || ny < 0 || ny > 1) return null;
      return [Number(nx.toFixed(4)), Number(ny.toFixed(4))];
    }

    _drawOverlay() {
      const canvas = this._canvas;
      const geo = this._geometry();
      if (!canvas || !geo) return;
      const dpr = window.devicePixelRatio || 1;
      const width = Math.max(1, Math.round(geo.rect.width * dpr));
      const height = Math.max(1, Math.round(geo.rect.height * dpr));
      if (canvas.width !== width || canvas.height !== height) {
        canvas.width = width;
        canvas.height = height;
      }
      const ctx = canvas.getContext("2d");
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, geo.rect.width, geo.rect.height);

      const px = (nx) => geo.x + nx * geo.w;
      const py = (ny) => geo.y + ny * geo.h;

      const drawPolygon = (points, color, fill, selected, label) => {
        if (!points || points.length < 2) return;
        ctx.beginPath();
        points.forEach(([nx, ny], index) => {
          if (index === 0) ctx.moveTo(px(nx), py(ny));
          else ctx.lineTo(px(nx), py(ny));
        });
        if (points.length > 2) {
          ctx.closePath();
          ctx.fillStyle = fill;
          ctx.fill();
        }
        ctx.strokeStyle = color;
        ctx.lineWidth = selected ? 3 : 2;
        ctx.stroke();
        points.forEach(([nx, ny]) => {
          ctx.beginPath();
          ctx.arc(px(nx), py(ny), selected ? 5 : 4, 0, Math.PI * 2);
          ctx.fillStyle = color;
          ctx.fill();
        });
        if (label && points.length) {
          ctx.font = "12px sans-serif";
          ctx.fillStyle = "rgba(0,0,0,.65)";
          const textWidth = ctx.measureText(label).width;
          ctx.fillRect(px(points[0][0]) - 2, py(points[0][1]) - 18, textWidth + 8, 16);
          ctx.fillStyle = "#fff";
          ctx.fillText(label, px(points[0][0]) + 2, py(points[0][1]) - 6);
        }
      };

      this._zones.forEach((zone, index) => {
        const exclude = zone.type === "exclude";
        drawPolygon(
          zone.points,
          exclude ? "#ffa726" : "#43a047",
          exclude ? "rgba(255,167,38,.20)" : "rgba(67,160,71,.20)",
          this._selected === index,
          zone.name || zone.id
        );
      });

      if (this._draft.length) {
        const points = this._pointer ? [...this._draft, this._pointer] : this._draft;
        drawPolygon(
          points,
          this._draftType === "exclude" ? "#ffb74d" : "#66bb6a",
          this._draftType === "exclude" ? "rgba(255,183,77,.16)" : "rgba(102,187,106,.16)",
          true,
          null
        );
      }

      const bbox = this._state?.bbox;
      if (bbox && this._state?.motion) {
        const [bx, by, bw, bh] = bbox;
        ctx.strokeStyle = "#ff1744";
        ctx.lineWidth = 2;
        ctx.setLineDash([6, 4]);
        ctx.strokeRect(px(bx), py(by), bw * geo.w, bh * geo.h);
        ctx.setLineDash([]);
      }
    }

    _onCanvasClick(event) {
      const point = this._toNormalized(event);
      if (!point) return;
      this._draft.push(point);
      this._drawOverlay();
    }

    _undoPoint() {
      if (!this._draft.length) return;
      this._draft.pop();
      this._drawOverlay();
    }

    _finishPolygon() {
      if (this._draft.length < 3) {
        this.toast(this.t("draw_hint"), "bad");
        return;
      }
      const index = this._zones.length + 1;
      const name = (this._draftName || "").trim() ||
        `${this._draftType === "exclude" ? this.t("type_exclude") : this.t("type_include")} ${index}`;
      this._zones.push({
        id: `zone-${Date.now().toString(36)}`,
        name,
        type: this._draftType,
        points: this._draft.slice(),
      });
      this._draft = [];
      this._draftName = "";
      if (this._nameInput) this._nameInput.value = "";
      this._selected = this._zones.length - 1;
      this._markDirty();
      this.toast(this.t("zone_added"));
    }

    _markDirty() {
      this._dirty = true;
      if (this._dirtyChip) this._dirtyChip.style.display = "";
      this._renderZoneList();
      this._drawOverlay();
    }

    // -------------------------------------------------------------- actions
    _buildConfig() {
      const base = this._state?.config || {};
      return {
        version: base.version || 1,
        enabled: base.enabled !== false,
        pixel_threshold: this._settings.pixel_threshold,
        min_motion_pixels: this._settings.min_motion_pixels,
        min_blob_pixels: this._settings.min_blob_pixels,
        trigger_frames: this._settings.trigger_frames,
        clear_frames: this._settings.clear_frames,
        warmup_frames: this._settings.warmup_frames,
        background_alpha: this._settings.background_alpha,
        foreground_alpha: this._settings.foreground_alpha,
        zones: this._zones.map((zone) => ({
          id: zone.id,
          name: zone.name,
          type: zone.type,
          points: zone.points,
        })),
      };
    }

    async _save() {
      if (this._draft.length >= 3) this._finishPolygon();
      if (this._saveButton) this._saveButton.disabled = true;
      try {
        const result = await this.ws("save_config", {
          entry_id: this._state.entry_id,
          config: this._buildConfig(),
        });
        if (result?.config) {
          this._state.config = result.config;
          this._adoptSettingsOnly(result.config);
        }
        this._dirty = false;
        this.toast(this.t("saved"));
      } catch (error) {
        this.toast(`${this.t("save_failed")}: ${error?.message || error}`, "bad");
      } finally {
        if (this._saveButton) this._saveButton.disabled = false;
        this._applyState();
      }
    }

    _adoptSettingsOnly(config) {
      Object.keys(this._settings).forEach((key) => {
        if (config[key] !== undefined) this._settings[key] = config[key];
      });
      Object.entries(this._sliders || {}).forEach(([key, control]) => {
        if (this._settings[key] === undefined) return;
        control.input.value = String(this._settings[key]);
        control.label.textContent = String(this._settings[key]);
      });
    }

    async _refreshDevice() {
      try {
        this._state = await this.ws("refresh", { entry_id: this._state.entry_id });
        if (!this._dirty) this._adoptDeviceState();
        this._render();
      } catch (error) {
        this.toast(String(error?.message || error), "bad");
      }
    }

    async _resetBackground() {
      try {
        await this.ws("reset_background", { entry_id: this._state.entry_id });
        this.toast(this.t("background_done"));
      } catch (error) {
        this.toast(String(error?.message || error), "bad");
      }
    }

    async _setEnabled(enabled) {
      try {
        await this.ws("set_enabled", { entry_id: this._state.entry_id, enabled });
        this._state.enabled = enabled;
        this._render();
      } catch (error) {
        this.toast(String(error?.message || error), "bad");
      }
    }

    async _setNotify(patch) {
      try {
        const state = await this.ws("notify", { entry_id: this._state.entry_id, ...patch });
        this._state = state;
        this._applyState();
      } catch (error) {
        this.toast(String(error?.message || error), "bad");
      }
    }

    async _testPush() {
      try {
        await this.ws("test_push", { entry_id: this._state.entry_id });
        this.toast(this.t("test_push_ok"));
      } catch (error) {
        this.toast(String(error?.message || error), "bad");
      }
    }

    async _setPreviewFps(fps) {
      try {
        const state = await this.ws("set_options", {
          entry_id: this._state.entry_id,
          preview_fps: fps,
        });
        this._state = state;
        this._applyState();
        // The MJPEG proxy keeps the old rate until the stream is reopened.
        this._startStream();
        this.toast(`${this.t("preview_fps")}: ${fps} fps`);
      } catch (error) {
        this.toast(String(error?.message || error), "bad");
      }
    }

    _closeDevice() {
      this._stopTimers();
      this._img = null;
      this._canvas = null;
      this._view = "device";
      this._render();
    }

    _backHome() {
      this._stopTimers();
      this._state = null;
      this._img = null;
      this._canvas = null;
      this._view = "home";
      this._loadDevices();
    }
  }

  customElements.define("recamera-motion-panel", RecameraMotionPanel);
})();
