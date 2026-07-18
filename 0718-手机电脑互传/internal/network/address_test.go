package network

import (
	"net"
	"testing"
)

func TestChoosePrivateIPv4PrefersWiFiAddress(t *testing.T) {
	addresses := []net.IP{
		net.ParseIP("127.0.0.1"),
		net.ParseIP("169.254.1.2"),
		net.ParseIP("192.168.31.20"),
	}

	got := ChoosePrivateIPv4(addresses)
	if got.String() != "192.168.31.20" {
		t.Fatalf("地址 = %s，期望 192.168.31.20", got)
	}
}

func TestPublicURLFormatsAddressAndPort(t *testing.T) {
	got := PublicURL(net.ParseIP("192.168.31.20"), 8765)
	if got != "http://192.168.31.20:8765" {
		t.Fatalf("URL = %q", got)
	}
}

func TestLocalIPv4AlwaysReturnsUsableAddress(t *testing.T) {
	address, err := LocalIPv4()
	if err != nil {
		t.Fatalf("LocalIPv4 返回错误：%v", err)
	}
	if address == nil || address.To4() == nil {
		t.Fatalf("地址不是 IPv4：%v", address)
	}
}
