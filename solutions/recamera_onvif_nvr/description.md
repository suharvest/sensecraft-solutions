## What this capability adds

Make a reCamera 2002W behave like a standard network camera for the systems you already use. Install once, then let a compatible NVR or video-management system find the camera through ONVIF instead of relying on a vendor-specific plug-in.

## What you get after deployment

- A discoverable camera service that compatible recorders can add from their ONVIF device list.
- A protected live H.264 video stream for recording or viewing.
- A direct path into Home Assistant's ONVIF integration, so the same camera can appear alongside your other smart-home cameras.

## Where to use it

- **NVR recording:** discover the reCamera from a compatible NVR and add it as a camera channel.
- **Video management:** use the camera in an existing VMS without maintaining a custom RTSP URL per vendor.
- **Home Assistant:** add the ONVIF integration with the camera address and view the live feed from a dashboard.

## Interfaces for system integration

The gateway provides an ONVIF service at port `8000` and a password-protected RTSP H.264 stream at port `8554`. Discovery uses WS-Discovery on UDP port `3702`; if multicast is blocked between network segments, add the ONVIF service URL manually.

## Usage notes

This package supports the RISC-V/musl reCamera 2002W generation only. One camera application can use the camera at a time. The default credentials are `admin` / `recamera.1`; restrict access on the local network and never expose the ONVIF or RTSP ports directly to the public internet.
