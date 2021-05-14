#
# Copyright (C) 2021 Nils Andreas Svee <me@lochnair.net>
#
# This is free software, licensed under the GNU General Public License v2.
# See /LICENSE for more information.
#

include $(TOPDIR)/rules.mk
include $(INCLUDE_DIR)/kernel.mk

PKG_NAME:=kmod-xt\_tls
PKG_VERSION:=0.3.1
PKG_RELEASE:=1

PKG_SOURCE:=$(PKG_NAME)-$(PKG_VERSION).tar.gz
PKG_SOURCE_URL:https://github.com/Lochnair/xt\_tls.git
PKG_SOURCE_PROTO:=git
PKG_SOURCE_SUBDIR=$(PKG_NAME)-$(PKG_VERSION)
PKG_SOURCE_VERSION:=99a11843cdff137c83bad41dfffb36083c9c9377

PKG_MAINTAINER:=Nils Andreas Svee <me@lochnair.net>
PKG_LICENSE=GPL-3.0
PKG_LICENSE_FILES=LICENSE

include $(INCLUDE_DIR)/package.mk

define KernelPackage/xt\_tls
	SUBMENU:=Other modules
	TITLE:=iptables module for filtering TLS connections
	FILES:=$(PKG_BUILD_DIR)/xt\_tls.ko
endef

define KernelPackage/xt\_tls/description
	A iptables module for filtering TLS connections.
endef

MAKE_OPTS:= \
	ARCH="$(LINUX_KARCH)" \
	CROSS_COMPILE="$(TARGET_CROSS)" \
	M="$(PKG_BUILD_DIR)"

define Build/Compile
	$(MAKE) -C "$(LINUX_DIR)" \
			$(MAKE_OPTS) \
			modules
endef

$(eval $(call KernelPackage,xt\_tls))
