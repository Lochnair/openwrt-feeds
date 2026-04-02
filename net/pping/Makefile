include $(TOPDIR)/rules.mk

PKG_NAME:=pping
PKG_VERSION:=2022-10-24
PKG_RELEASE:=1

PKG_SOURCE_PROTO:=git
PKG_SOURCE_URL:=https://github.com/pollere/$(PKG_NAME).git
PKG_SOURCE:=$(PKG_NAME)-$(PKG_VERSION).tar.xz
PKG_SOURCE_VERSION:=6cc6a604916d29415bd2c8f51f8be8900f6c83c8

PKG_MAINTAINER:=Nils Andreas Svee <contact@lochnair.net>
PKG_LICENSE:=GPL-2.0

include $(INCLUDE_DIR)/package.mk

define Package/pping
  SECTION:=utils
  CATEGORY:=Utilities
  TITLE:=pping
  URL:=https://github.com/pollere/pping
  DEPENDS:=+libtins
endef

define Package/pping/description
  pping is a linux/macOS/BSD command line tool to measure network latency via passive monitoring of active connections
endef

define Build/Compile
	$(TARGET_CXX) -o $(PKG_BUILD_DIR)/pping -ltins -lpcap $(PKG_BUILD_DIR)/pping.cpp
endef

define Package/pping/install
	$(INSTALL_DIR) $(1)/usr/bin
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/pping $(1)/usr/bin/pping
endef

$(eval $(call BuildPackage,pping))
