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
#include <linux/kfifo.h>
#include <linux/cdev.h>
#include <linux/gpio.h>
#include <linux/uaccess.h>
#include <linux/delay.h>

#define FIFO_SIZE 1024
#define MSG_FIFO_MAX 1024
#define BUF_LEN 1024

#define LOG_FORMAT "DSC keybus: %s\n"
#define LOG_FORMAT_1D "DSC keybus: %s => %d\n"
#define LOG_FORMAT_1H "DSC keybus: %s => %#04X\n"

unsigned long timer_interval_ns = 1e9L;
static int dsc_major;
static struct hrtimer blink_timer;
static short int dev_open = false;

static DECLARE_KFIFO(dsc_write_fifo, char, FIFO_SIZE);

struct dsc_dev
{
    int idx_r;
    int idx_w;
    dev_t dev;
    struct class *cl;
    struct device *dv;
    struct kfifo r_fifo;
    struct kfifo w_fifo;
    int msg_len[MSG_FIFO_MAX];
    char cur_msg[BUF_LEN];
    bool binary;
    char *name;
    struct semaphore sem;
    struct cdev cdev;
    bool open;
};

static struct dsc_dev dsc_txt = {
    .binary = false,
    .name = "dsc_txt"};

#define DSC_CLOCK 0
#define DSC_DATA  1
static struct gpio keybus[] = {
    {5, GPIOF_OUT_INIT_HIGH, "DSC CLK"},  // KeyBus Clock
    {0, GPIOF_OUT_INIT_HIGH, "DSC DATA"}, // KeyBus Data
};

#define CMD_STATUS 0x05

// static struct dsc_dev dsc_bin = {
// 	.binary = true,
// 	.name = "dsc_bin"
// };

// static struct dsc_dev * dsc_devs[] = {
// 	&dsc_txt,
// 	&dsc_bin
// };

int dsc_dev_init(struct dsc_dev *device, int index);
void dsc_dev_destroy(struct dsc_dev *device);
static int dsc_dev_open(struct inode *, struct file *);
static int dsc_dev_close(struct inode *, struct file *);
static ssize_t dsc_read(struct file *, char *, size_t, loff_t *);
static ssize_t dsc_write(struct file *, const char *, size_t, loff_t *);

static struct file_operations file_operations = {
    .read = dsc_read,
    .write = dsc_write,
    .open = dsc_dev_open,
    .release = dsc_dev_close,
    .owner = THIS_MODULE
};


void write_bit(bool bit) {
    // write command
    gpio_direction_output(keybus[DSC_CLOCK].gpio, 0);
    udelay(20);
    gpio_direction_output(keybus[DSC_DATA].gpio, 1);
    udelay(430);
    pr_info(LOG_FORMAT_1D, "Sending value", bit);
    gpio_direction_output(keybus[DSC_DATA].gpio, bit);
    udelay(60);
    gpio_direction_output(keybus[DSC_CLOCK].gpio, 1);
    udelay(490);
}

void write_byte(short int byte) {
    int i;
    for (i = 7; i >= 0; --i)
    {
        // pr_info(LOG_FORMAT_1D, "Sending index", i);
        write_bit((byte >> i) & 0x01);
    }
}

bool read_bit(void) {
    short int bit = 0;
    gpio_direction_input(keybus[DSC_DATA].gpio);

    // gpio_direction_output(keybus[DSC_CLOCK].gpio, 0);
    // udelay(200);
    // bit = gpio_get_value(keybus[DSC_DATA].gpio);
    // pr_info(LOG_FORMAT_1D, "Reading value =", bit);
    // udelay(300);
    // gpio_direction_output(keybus[DSC_CLOCK].gpio, 1);
    // udelay(500);
    gpio_direction_output(keybus[DSC_CLOCK].gpio, 0);
    udelay(200);
    bit = gpio_get_value(keybus[DSC_DATA].gpio);
    pr_info(LOG_FORMAT_1D, "Reading value =", bit);
    udelay(300);
    gpio_direction_output(keybus[DSC_CLOCK].gpio, 1);
    udelay(500);

    return bit;
}

/*
 * Periodically called function.
 */
static enum hrtimer_restart communicate(struct hrtimer *timer)
{
    int response = 0;
    ktime_t currtime, interval;
    // pr_info(LOG_FORMAT, "Start communication");

    gpio_direction_output(keybus[DSC_CLOCK].gpio, 1);
    gpio_direction_output(keybus[DSC_DATA].gpio, 1);

    pr_info(LOG_FORMAT_1D, "Send command", CMD_STATUS);
    write_byte(CMD_STATUS);

    // udelay(1000);
    read_bit();

    if (read_bit() == 0) {
        int i;
        for (i = 0; i < 8; ++i) {
            response = (response << 1) | read_bit();
        }

        pr_info(LOG_FORMAT_1H, "Received response = ", response);
    }
    else {
        pr_info(LOG_FORMAT, "No response received");
    }


    udelay(2000);
    // write_byte(0x27);

    // write_byte(0xFF);

    gpio_direction_output(keybus[DSC_CLOCK].gpio, 1);
    gpio_direction_output(keybus[DSC_DATA].gpio, 1);

    currtime = ktime_get();
	interval = ktime_set(0,timer_interval_ns);
	hrtimer_forward(timer, currtime , interval);

    pr_info(LOG_FORMAT, "End communication");
    // pr_info(LOG_FORMAT, "Command sent");
    return HRTIMER_RESTART;
}


/*
 * Module init function
 */
static int __init dsc_keybus_mod_init(void)
{
    ktime_t blink_time = ktime_set(0, timer_interval_ns);
    pr_info(LOG_FORMAT, "initializing DSC keybus master module");
    pr_info(LOG_FORMAT, "period created");

    hrtimer_init(&blink_timer, CLOCK_MONOTONIC, HRTIMER_MODE_REL);
    blink_timer.function = &communicate;
    pr_info(LOG_FORMAT, "timer initialized");

    hrtimer_start(&blink_timer, blink_time, HRTIMER_MODE_REL);
    pr_info(LOG_FORMAT, "timer started");

    INIT_KFIFO(dsc_write_fifo);

    dsc_dev_init(&dsc_txt, 0);
    // dsc_dev_init(&dsc_bin, 1);

    gpio_direction_output(keybus[DSC_CLOCK].gpio, 1);
    gpio_direction_output(keybus[DSC_DATA].gpio, 1);

    pr_info(LOG_FORMAT, "initialized module");
    return 0;
}

/*
 * Module exit function
 */
static void __exit dsc_keybus_mod_exit(void)
{
    pr_info(LOG_FORMAT, "exiting DSC keybus master module");

    // deactivate timer if running
    hrtimer_cancel(&blink_timer);
    pr_info(LOG_FORMAT, "cancelled timer");

    dsc_dev_destroy(&dsc_txt);
    pr_info(LOG_FORMAT, "destroyed txt");
    // dsc_dev_destroy(&dsc_bin);
    // pr_info(LOG_FORMAT, "destroyed bin");

    pr_info(LOG_FORMAT, "exited");
}

static int dsc_msg_to_fifo(struct kfifo *fifo, char *msg, int len)
{
    unsigned int copied;
    if (kfifo_avail(fifo) < len)
    {
        printk_ratelimited(KERN_ERR "No space left in FIFO for %d\n", len);
        return -ENOSPC;
    }
    copied = kfifo_in(fifo, msg, len);
    if (copied != len)
    {
        pr_err(LOG_FORMAT, "short write to FIFO");
    }

    return copied;
}

static ssize_t dsc_read(struct file *pfile, char __user *buffer, size_t length, loff_t *offset)
{
    int retval;
    unsigned int copied = 0;

    struct dsc_dev *device = pfile->private_data;
    struct kfifo *fifo = &device->r_fifo;
    pr_info(LOG_FORMAT, "reading message");

    if (length < device->msg_len[device->idx_r])
    {
        pr_warning(LOG_FORMAT, "stored msg longer than read");
    }
    retval = kfifo_to_user(fifo, buffer, (length >= device->msg_len[device->idx_r]) ? device->msg_len[device->idx_r] : length, &copied);
    if (retval == 0 && (copied != device->msg_len[device->idx_r]))
    {
        pr_warning(LOG_FORMAT, "short read from fifo");
    }
    else if (retval != 0)
    {
        pr_warning(LOG_FORMAT, "error reading from kfifo");
    }
    device->idx_r = (device->idx_r + 1) % MSG_FIFO_MAX;

    return retval ? retval : copied;
}

static ssize_t dsc_write(struct file *pfile, const char *buff, size_t len, loff_t *off)
{
    int ret;
    char kbuf[FIFO_SIZE];
    int copy_max = len < FIFO_SIZE ? len : FIFO_SIZE;
    pr_info(LOG_FORMAT, "writing message");

    ret = copy_from_user(kbuf, buff, copy_max);
    if (ret != 0)
    {
        pr_warning(LOG_FORMAT, "short write");
    }

    pr_info(LOG_FORMAT, buff);

    dsc_msg_to_fifo((struct kfifo *)&dsc_write_fifo, kbuf, copy_max);
    return copy_max;
}

int dsc_dev_init(struct dsc_dev *device, int index)
{
    int ret1, ret2;
    dev_t dev;
    device->idx_r = 0;
    device->idx_w = 0;
    device->open = false;
    ret1 = kfifo_alloc(&(device->r_fifo), FIFO_SIZE, GFP_KERNEL);
    ret2 = kfifo_alloc(&(device->w_fifo), FIFO_SIZE, GFP_KERNEL);
    if (ret1 || ret2)
    {
        pr_err(LOG_FORMAT, "error in kfifo_alloc");
        return -1;
    }

    cdev_init(&device->cdev, &file_operations);
    ret1 = alloc_chrdev_region(&dev, 0, 1, device->name);
    dsc_major = MAJOR(dev);
    if (ret1 < 0)
    {
        pr_warning(LOG_FORMAT, "couldn't get major ");
        return -1;
    }

    ret2 = cdev_add(&device->cdev, dev, 1);
    if (ret2)
    {
        pr_warning(LOG_FORMAT, "error adding device: ");
        return ret2;
    }

    device->cl = class_create(THIS_MODULE, device->name);
    if (IS_ERR(device->cl))
    {
        pr_warning(LOG_FORMAT, "error creating class");
        return -1;
    }

    device->dv = device_create(device->cl, NULL, dev, NULL, device->name);
    if (IS_ERR(device->dv))
    {
        pr_warning(LOG_FORMAT, "error creating dev");
        class_destroy(device->cl);
        return -1;
    }

    device->dev = dev;
    return (ret1 | ret2);
}

void dsc_dev_destroy(struct dsc_dev *device)
{
    device_destroy(device->cl, device->dev);
    class_destroy(device->cl);
}

static int dsc_dev_open(struct inode *inode, struct file *pfile)
{
    struct dsc_dev *dev;
    pr_info(LOG_FORMAT, "Opening device");
    if (dev_open > 0)
        return -EBUSY;
    dev = container_of(inode->i_cdev, struct dsc_dev, cdev);
    dev->open = true;
    pfile->private_data = dev;
    //memset(cur_msg_bin, 0, BUF_LEN);
    dev_open++;
    pr_info(LOG_FORMAT, "Opened device");
    return 0;
}

static int dsc_dev_close(struct inode *inode, struct file *pfile)
{
    struct dsc_dev *dev;
    dev = container_of(inode->i_cdev, struct dsc_dev, cdev);
    dev->open = false;
    dev_open--;
    return 0;
}

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Gábor Kovács (gkovacs81@gmail.com)");
MODULE_DESCRIPTION(
    "Kernel module for implementing DSC keybus protocol - master");

module_init(dsc_keybus_mod_init);
module_exit(dsc_keybus_mod_exit);
