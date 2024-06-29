include $(TOPDIR)/rules.mk

PKG_NAME:=lua-vstruct
PKG_VERSION:=2.1.1
PKG_RELEASE:=1

PKG_SOURCE:=$(PKG_NAME)-$(PKG_VERSION).tar.gz
PKG_SOURCE_URL:=https://codeload.github.com/ToxicFrog/vstruct/tar.gz/v$(PKG_VERSION)?
PKG_HASH:=029ae887fc3c59279f378a499741811976d90f9a806569a42f4de80ad349f333

PKG_MAINTAINER:=Nils Andreas Svee <contact@lochnair.net>
PKG_LICENSE:=MIT
PKG_LICENSE_FILES:=COPYING

PKG_BUILD_DIR:=$(BUILD_DIR)/vstruct-$(PKG_VERSION)

include $(INCLUDE_DIR)/package.mk

define Package/lua-vstruct
  SUBMENU:=Lua
  SECTION:=lang
  CATEGORY:=Languages
  TITLE:=A Lua library for packing and unpacking binary data
  URL:=https://github.com/ToxicFrog/vstruct
  PKGARCH:=all
endef

define Package/lua-vstruct/desription
  A Lua library for packing and unpacking binary data,
  supporting arbitrary (byte-aligned) widths, named fields, and repetition.
endef

define Build/Compile
endef

# Note: I left out the test files
define Package/lua-vstruct/install
	$(INSTALL_DIR) $(1)/usr/lib/lua/vstruct
	$(INSTALL_DATA) \
		$(PKG_BUILD_DIR)/*.lua \
		$(1)/usr/lib/lua/vstruct/
	$(INSTALL_DIR) $(1)/usr/lib/lua/vstruct/ast
	$(INSTALL_DATA) \
		$(PKG_BUILD_DIR)/ast/*.lua \
		$(1)/usr/lib/lua/vstruct/ast/
	$(INSTALL_DIR) $(1)/usr/lib/lua/vstruct/io
	$(INSTALL_DATA) \
		$(PKG_BUILD_DIR)/io/*.lua \
		$(1)/usr/lib/lua/vstruct/io/
endef

$(eval $(call BuildPackage,lua-vstruct))
