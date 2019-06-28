cflags-y +=-I/lib/modules/$(shell uname -r)/build/include
obj-m += dsc_keybus_master.o

ifdef CREAD
    ccflags-y += -DCREAD=${CREAD}
endif

all: 
	make -C /lib/modules/$(shell uname -r)/build M=$(PWD) modules 

clean:
	make -C /lib/modules/$(shell uname -r)/build M=$(PWD) clean