include $(TOPDIR)/rules.mk

PKG_NAME:=tsping
PKG_VERSION:=0.1
PKG_RELEASE:=1

PKG_SOURCE_PROTO:=git
PKG_SOURCE_URL:=https://github.com/Lochnair/tsping
PKG_SOURCE_VERSION:=a413a5bf851de622eb93ab11a07a4ed607b81878

PKG_MAINTAINER:=Nils Andreas Svee <contact@lochnair.net>
PKG_LICENSE:=BSD-3-Clause
PKG_LICENSE_FILES:=LICENSE.md

PKG_INSTALL:=1
PKG_BUILD_PARALLEL:=1
PKG_BUILD_DEPENDS:=!USE_GLIBC:argp-standalone

include $(INCLUDE_DIR)/package.mk
include $(INCLUDE_DIR)/meson.mk

MESON_ARGS += \
	$(if $(USE_GLIBC), -Dargp_standalone=false, -Dargp_standalone=true)

define Package/tsping
  SECTION:=utils
  CATEGORY:=Utilities
  TITLE:=Utility for sending timestamp pings
  URL:=https://github.com/Lochnair/tsping
endef

define Package/tsping/description
  A simple application to send ICMP echo/timestamp requests
endef

define Package/tsping/install
	$(INSTALL_DIR) $(1)/usr/sbin
	$(INSTALL_BIN) $(MESON_BUILD_DIR)/tsping $(1)/usr/sbin/
endef

$(eval $(call BuildPackage,tsping))
