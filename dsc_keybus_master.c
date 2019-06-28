/*
 ============================================================================
 Name        : dsc_keybus_master.c
 Author      : Gábor Kovács
 Version     :
 Copyright   :
 Description : Hello World in C, Ansi-style
 ============================================================================
 */

#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/hrtimer.h>
#include <linux/gpio.h>

#define LED1 27

unsigned long timer_interval_ns = 1e6L;
static struct hrtimer blink_timer;

/*
 * Periodically called function.
 */
static enum hrtimer_restart blink_timer_func(struct hrtimer *timer) {
	ktime_t currtime , interval;
	printk(KERN_INFO "Calling timer! - kovg\n");

	currtime = ktime_get();
	interval = ktime_set(0,timer_interval_ns);
	hrtimer_forward(timer, currtime , interval);

	// register, turn off
//	int ret = gpio_request_one(LED1, GPIOF_OUT_INIT_LOW, "led1");
//
//	if (ret) {
//		printk(KERN_ERR "Unable to request GPIOs: %d\n", ret);
//		return ret;
//	}

	printk(KERN_INFO "Called timer! - kovg\n");
	return HRTIMER_RESTART;
}


/*
 * Module init function
 */
static int __init dsc_keybus_mod_init(void) {
	ktime_t blink_time = ktime_set(0, timer_interval_ns);
	printk(KERN_INFO "Initializing! - kovg\n");
	printk(KERN_INFO "Period created! - kovg\n");

	hrtimer_init(&blink_timer, CLOCK_MONOTONIC, HRTIMER_MODE_REL);
	blink_timer.function = &blink_timer_func;
	printk(KERN_INFO "Timer initialized! - kovg\n");

	hrtimer_start(&blink_timer, blink_time, HRTIMER_MODE_REL);
	printk(KERN_INFO "Initialized! - kovg\n");

	return 0;
}

/*
 * Module exit function
 */
static void __exit dsc_keybus_mod_exit(void) {
printk(KERN_INFO "%s\n", __func__);

// deactivate timer if running
hrtimer_cancel(&blink_timer);

//	// turn LED off
//	gpio_set_value(LED1, 0);
//
//	// unregister GPIO
//	gpio_free(LED1);
	printk(KERN_INFO "Exiting! - kovg");
}

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Gábor Kovács (gkovacs81@gmail.com)");
MODULE_DESCRIPTION(
	"Kernel module for implementing DSC keybus protocol - master");

module_init(dsc_keybus_mod_init);
module_exit(dsc_keybus_mod_exit);
