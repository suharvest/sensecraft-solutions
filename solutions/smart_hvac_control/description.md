## What This Solution Does

HVAC systems in office buildings, shopping malls, and factories often run on fixed schedules - blasting cold air in empty rooms while struggling to keep busy areas comfortable. This solution makes your HVAC system "smart" by automatically adjusting temperature based on occupancy and environmental conditions, running efficiently when needed and saving energy when not.

## Key Benefits

| Benefit | Details |
|---------|---------|
| Automatic Energy Savings | Intelligently adjusts based on real-time occupancy and outdoor temperature, typically saving 15-25% on electricity |
| No Manual Monitoring | System runs 24/7 automatically, no need for someone to constantly adjust parameters |
| Quick Setup | Upload historical data and the system learns on its own - no HVAC expertise required |
| Safe & Controlled | "Observe first" mode lets you verify suggestions before enabling automatic control |

## Use Cases

| Scenario | How It Helps |
|----------|--------------|
| Office Buildings | Cools more during busy work hours, automatically saves energy after hours; switches to eco-mode on weekends |
| Shopping Malls | Adjusts cooling per floor based on foot traffic - less cooling where its quiet, more where its crowded |
| Factory Floors | Syncs with production schedules, reducing HVAC power during off-shifts |
| Hotel Lobbies | Dynamically adjusts based on occupancy rates and outdoor temperature for comfort and efficiency |

## Requirements

**Hardware**:
- reComputer R1100 edge computing device
- HVAC controller must support industrial communication protocol (OPC-UA)

**Data**:
- At least 1 week of historical operation data (Excel or CSV format)
- Data should include: timestamp, temperature setpoints, actual temperature, power consumption

**Limitations**:
- Initial setup requires uploading data for the system to learn (takes about 5-10 minutes)
- Recommended to observe system suggestions for 1-2 days before enabling automatic control
- This solution is designed for central HVAC systems, not split-unit air conditioners
