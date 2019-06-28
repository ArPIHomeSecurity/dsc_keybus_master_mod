#include <linux/module.h>
#include <linux/vermagic.h>
#include <linux/compiler.h>

MODULE_INFO(vermagic, VERMAGIC_STRING);

__visible struct module __this_module
__attribute__((section(".gnu.linkonce.this_module"))) = {
	.name = KBUILD_MODNAME,
	.init = init_module,
#ifdef CONFIG_MODULE_UNLOAD
	.exit = cleanup_module,
#endif
	.arch = MODULE_ARCH_INIT,
};

#ifdef RETPOLINE
MODULE_INFO(retpoline, "Y");
#endif

static const struct modversion_info ____versions[]
__used
__attribute__((section("__versions"))) = {
	{ 0xa8df3833, __VMLINUX_SYMBOL_STR(module_layout) },
	{ 0xa5842a74, __VMLINUX_SYMBOL_STR(hrtimer_cancel) },
	{ 0x616d2605, __VMLINUX_SYMBOL_STR(hrtimer_start_range_ns) },
	{ 0xf87aa8bc, __VMLINUX_SYMBOL_STR(hrtimer_init) },
	{ 0x5861be08, __VMLINUX_SYMBOL_STR(hrtimer_forward) },
	{ 0xc87c1f84, __VMLINUX_SYMBOL_STR(ktime_get) },
	{ 0x50eedeb8, __VMLINUX_SYMBOL_STR(printk) },
	{ 0xb4390f9a, __VMLINUX_SYMBOL_STR(mcount) },
};

static const char __module_depends[]
__used
__attribute__((section(".modinfo"))) =
"depends=";

