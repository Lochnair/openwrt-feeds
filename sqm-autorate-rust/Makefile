# SPDX-License-Identifier: GPL-2.0-only
#
# Copyright (C) 2023 Nils Andreas Svee

include $(TOPDIR)/rules.mk

PKG_NAME:=sqm-autorate-rust
PKG_VERSION:=0.1
PKG_RELEASE:=1

PKG_SOURCE_PROTO:=git
PKG_SOURCE_URL:=https://github.com/Lochnair/sqm-autorate-rust
PKG_SOURCE_VERSION:=4a1368cd7ae4ad9960fcdf4a2f42672f49863fad

PKG_MAINTAINER:=Nils Andreas Svee <me@lochnair.net>
PKG_LICENSE:=MPL

PKG_BUILD_DEPENDS:=rust/host

include $(TOPDIR)/feeds/packages/lang/rust/rust-package.mk
include $(INCLUDE_DIR)/package.mk

define Build/Compile
	$(call Build/Compile/Cargo,,)
endef

define Package/sqm-autorate-rust
  SECTION:=utils
  CATEGORY:=Utilities
  TITLE:=sqm autorate (rust)
  DEPENDS:=$(RUST_ARCH_DEPENDS)
  URL:=https://github.com/Lochnair/sqm-autorate-rust
endef

define Package/sqm-autorate-rust/description
  Rust port of the Lua implementation of CAKE autorate
endef

define Package/sqm-autorate-rust/install
	$(INSTALL_DIR) $(1)/usr/sbin
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/target/$(RUSTC_TARGET_ARCH)/stripped/sqm-autorate-rust $(1)/usr/sbin/sqm-autorate-rust
endef

$(eval $(call BuildPackage,sqm-autorate-rust))
