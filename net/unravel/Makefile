# SPDX-License-Identifier: GPL-2.0-only
#
# Copyright (C) 2023 Nils Andreas Svee

include $(TOPDIR)/rules.mk

PKG_NAME:=unravel
PKG_VERSION:=0.5.0-rc1
PKG_RELEASE:=1

PKG_SOURCE_PROTO:=git
PKG_SOURCE_URL:=https://github.com/Lochnair/unravel
PKG_SOURCE_VERSION:=5a13d298d87edae7243b69dc7d6ea8fc5b9cfba2

PKG_MAINTAINER:=Nils Andreas Svee <me@lochnair.net>
PKG_LICENSE:=MPL

PKG_BUILD_DEPENDS:=rust/host
RUST_PKG_FEATURES:=irtt,uci

include $(INCLUDE_DIR)/package.mk
include $(TOPDIR)/feeds/packages/lang/rust/rust-package.mk

CARGO_PKG_VARS += UCI_DIR=$(STAGING_DIR)/usr \
    LIBCLANG_PATH=$(STAGING_DIR_HOST)/llvm-bpf/lib \
    BINDGEN_EXTRA_CLANG_ARGS="-I$(STAGING_DIR)/usr/include --sysroot=$(TOOLCHAIN_DIR)"

define Build/Compile
	$(call Build/Compile/Cargo,,)
endef

define Package/unravel
  SECTION:=utils
  CATEGORY:=Utilities
  TITLE:=unRAVEL
  DEPENDS:=$(RUST_ARCH_DEPENDS) +libuci
  URL:=https://github.com/Lochnair/unravel
endef

define Package/unravel/description
  unRAVEL (Rate Adaptation Via Event-driven Logic) adjusts CAKE traffic shaping rates to keep latency under control on connections with fluctuating bandwidth
endef

define Package/unravel/install
	$(INSTALL_DIR) $(1)/etc/config $(1)/etc/unravel $(1)/etc/init.d $(1)/usr/sbin $(1)/usr/lib/unravel
	$(INSTALL_BIN) $(PKG_INSTALL_DIR)/bin/unravel $(1)/usr/sbin/unravel
	$(INSTALL_CONF) \
		$(PKG_BUILD_DIR)/reflectors.csv \
		$(1)/etc/unravel/reflectors.csv
	$(INSTALL_BIN) \
		./files/configure.sh \
		$(1)/usr/lib/unravel/
	$(INSTALL_BIN) \
		./files/unravel.service \
		$(1)/etc/init.d/unravel
	$(INSTALL_CONF) \
		./files/unravel.config \
		$(1)/etc/config/unravel
endef

$(eval $(call RustBinPackage,unravel))
$(eval $(call BuildPackage,unravel))
