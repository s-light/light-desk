# PocketBeagle Internet Sharing via NetworkManager (Kubuntu)

Setup notes for sharing the host's internet connection with a PocketBeagle
over the USB network interface, using NetworkManager instead of manual
`iptables`/`sysctl` commands.

- Host interface: `enx0447072dc71a` (USB network device, name will vary by MAC)
- Host IP: `192.168.17.1`
- Board IP: `192.168.17.2` (static, `/30` subnet)
- Board OS network manager: `systemd-networkd`

---

## 1. Host side (Kubuntu / NetworkManager)

Create/modify the NM connection profile for the PocketBeagle's USB interface.
Replace `"pocketBeagle"` with your connection name and `enx0447072dc71a` with
your actual interface name (`nmcli device status` to check).

```bash
nmcli connection modify "pb_6ch-light-desk" \
  ipv4.method shared \
  ipv4.addresses 192.168.17.1/24
nmcli connection down "pb_6ch-light-desk"
nmcli connection up "pb_6ch-light-desk"
nmcli connection show "pb_6ch-light-desk"
```


This makes NetworkManager automatically:
- enable `net.ipv4.ip_forward=1`
- set up NAT/MASQUERADE from the USB interface to whatever holds your
  default route (wifi, ethernet, etc. — no need to hardcode it)
- persist across reboots (unlike manual `iptables`/`sysctl` commands)

### Verify on the host

```bash
ip addr show enx0447072dc71a          # should show 192.168.17.1/24
cat /proc/sys/net/ipv4/ip_forward     # should be 1
sudo iptables -t nat -L POSTROUTING -n -v   # should show a MASQUERADE rule
```

---

## 2. Board side (systemd-networkd)

Edit the network file for the USB interface:

```bash
sudo nano /etc/systemd/network/usb0.network
```

Ensure it looks like this (add the `[Route]` section if missing):

```ini
[Match]
Name=usb0

[Link]
RequiredForOnline=no

[Network]
Address=192.168.17.2/30
DHCP=no
DHCPServer=true
DNS=9.9.9.9

[DHCPServer]
PoolSize=1
MaxLeaseTimeSec=20min
EmitDNS=no
EmitRouter=yes
EmitTimezone=no
PersistLeases=runtime

[Route]
Gateway=192.168.17.1
```

Apply the changes:

```bash
sudo systemctl restart systemd-networkd
ip route        # should show: default via 192.168.17.1 dev usb0
```

### DNS on the board

If `/etc/resolv.conf` is a  symlink - check with 

```bash
ls -l /etc/resolv.conf
```

DNS is already handled via `DNS=9.9.9.9` in the `usb0.network` file above 
`/etc/resolv.conf` should update automatically.

---

## 3. Test from the board

```bash
ping -c3 192.168.17.1      # link to host
ping -c3 9.9.9.9           # routing + NAT
ping -c3 google.com        # DNS
```

All three should succeed once both sides are configured.
