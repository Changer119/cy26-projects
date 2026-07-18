package auth

import "testing"

func TestSessionAuthorizesOnlyItsBearerToken(t *testing.T) {
	session, err := NewSession()
	if err != nil {
		t.Fatalf("NewSession 返回错误：%v", err)
	}

	if !session.Authorize("Bearer " + session.Token()) {
		t.Fatal("正确的 Bearer Token 应通过认证")
	}
	for _, header := range []string{"", session.Token(), "Bearer wrong-token", "Basic " + session.Token()} {
		if session.Authorize(header) {
			t.Fatalf("认证头 %q 不应通过", header)
		}
	}
}

func TestSessionTokenHasEnoughEntropy(t *testing.T) {
	session, err := NewSession()
	if err != nil {
		t.Fatal(err)
	}
	if len(session.Token()) < 40 {
		t.Fatalf("令牌长度 = %d，期望至少 40 个字符", len(session.Token()))
	}
}
