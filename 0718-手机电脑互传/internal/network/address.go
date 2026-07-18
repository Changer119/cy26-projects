package network

import (
	"net"
	"strconv"
)

func ChoosePrivateIPv4(addresses []net.IP) net.IP {
	for _, address := range addresses {
		if address.To4() != nil && address.IsPrivate() {
			return address.To4()
		}
	}
	return net.ParseIP("127.0.0.1").To4()
}

func PublicURL(address net.IP, port int) string {
	return "http://" + net.JoinHostPort(address.String(), strconv.Itoa(port))
}

func LocalIPv4() (net.IP, error) {
	interfaceAddresses, err := net.InterfaceAddrs()
	if err != nil {
		return nil, err
	}
	addresses := make([]net.IP, 0, len(interfaceAddresses))
	for _, interfaceAddress := range interfaceAddresses {
		address, _, parseErr := net.ParseCIDR(interfaceAddress.String())
		if parseErr == nil {
			addresses = append(addresses, address)
		}
	}
	return ChoosePrivateIPv4(addresses), nil
}
