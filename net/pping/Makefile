include $(TOPDIR)/rules.mk

PKG_NAME:=pping
PKG_VERSION:=777eb72
PKG_RELEASE:=1

PKG_SOURCE_PROTO:=git
PKG_SOURCE_URL:=https://github.com/pollere/$(PKG_NAME).git
PKG_SOURCE:=$(PKG_NAME)-$(PKG_VERSION).tar.xz
PKG_SOURCE_VERSION:=777eb72fd9b748b4bb628ef97b7fff19b751f1fd

PKG_MAINTAINER:=Nils Andreas Svee <contact@lochnair.net>
PKG_LICENSE:=GPL-2.0

include $(INCLUDE_DIR)/package.mk

define Package/pping
  SECTION:=utils
  CATEGORY:=Utilities
  TITLE:=pping
  URL:=https://github.com/pollere/pping
  DEPENDS:=+libc +libm +libtins +libpcap
endef

define Package/pping/description
  pping is a linux/macOS/BSD command line tool to measure network latency via passive monitoring of active connections
endef

define Build/Compile
	LIBTINS=$(STAGING_DIR) $(MAKE) -C $(PKG_BUILD_DIR)
endef

define Package/pping/install
	$(INSTALL_DIR) $(1)/usr/bin
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/pping $(1)/usr/bin/pping
endef

$(eval $(call BuildPackage,pping))
