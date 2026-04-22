# SPDX-License-Identifier: GPL-2.0-only
#
# Copyright (C) 2023 Nils Andreas Svee

include $(TOPDIR)/rules.mk

PKG_NAME:=sqm-autorate-rust
PKG_VERSION:=0.4.1
PKG_RELEASE:=1

PKG_SOURCE_PROTO:=git
PKG_SOURCE_URL:=https://github.com/Lochnair/sqm-autorate-rust
PKG_SOURCE_VERSION:=8739ed4419f4d38dfd62116d8fbc40177637e31d

PKG_MAINTAINER:=Nils Andreas Svee <me@lochnair.net>
PKG_LICENSE:=MPL

PKG_BUILD_DEPENDS:=rust/host
RUST_PKG_FEATURES:=uci

include $(TOPDIR)/feeds/packages/lang/rust/rust-package.mk
include $(INCLUDE_DIR)/package.mk

LLVM_BPF_DIR:=$(wildcard $(STAGING_DIR_HOST)/llvm-bpf-*)
CARGO_PKG_VARS += UCI_DIR=$(STAGING_DIR)/usr LIBCLANG_PATH=$(LLVM_BPF_DIR)/lib

define Build/Compile
	$(info CARGO_PKG_VARS is: $(CARGO_PKG_VARS))
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
	$(INSTALL_DIR) $(1)/etc/config $(1)/etc/sqm-autorate/rust $(1)/etc/init.d $(1)/usr/sbin $(1)/usr/lib/sqm-autorate-rust
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/target/$(RUSTC_TARGET_ARCH)/stripped/sqm-autorate-rust $(1)/usr/sbin/sqm-autorate-rust
	$(INSTALL_CONF) \
		./files/reflectors-icmp.csv \
		$(1)/etc/sqm-autorate-rust/reflectors-icmp.csv
	$(INSTALL_BIN) \
		./files/configure.sh \
		$(1)/usr/lib/sqm-autorate-rust/
	$(INSTALL_BIN) \
		./files/sqm-autorate-rust.service \
		$(1)/etc/init.d/sqm-autorate-rust
	$(INSTALL_CONF) \
		./files/sqm-autorate-rust.config \
		$(1)/etc/config/sqm-autorate-rust
endef

$(eval $(call BuildPackage,sqm-autorate-rust))
