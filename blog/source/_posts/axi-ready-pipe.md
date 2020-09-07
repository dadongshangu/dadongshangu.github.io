---
title: 握手协议（pvld/prdy或者valid-ready或AXI）中ready打拍技巧
date: 2020-09-07 22:48:43
tags: verilog
---

## 内容提要

- ready打拍的问题
- 用FIFO的思路去解决
- 用Buffer的思路去解决

## 问题提出：ready时序如何优化？

在valid/ready 握手协议中，valid 与 data的时序优化比较容易理解，（不熟悉valid/ready协议或者valid打拍方法的）大家可以参考上次推送（[握手协议（pvld/prdy或者valid-ready或AXI）中Valid及data打拍技巧](http://mp.weixin.qq.com/s?__biz=MzIxMjg2ODQxMw==&mid=2247483672&idx=1&sn=62a940a7ec6d84a7da991ab14f4e1d7c&chksm=97becd4aa0c9445cefdab5bb3ec7f8c6400e7ef9702f6369ab88924a5cba118e122a07b17d16&scene=21#wechat_redirect)）。
但是有时候，关键路径是在ready信号上，如何对ready信号打拍呢？


首先将把目标设计想象成一个黑盒子,如图1所示，我们的目标是将READY_DOWN通过打拍的方法获得时序优化。

![img](https://cdn.jsdelivr.net/gh/dadongshangu/CDN@master/images/20200907_black_box.JPG)

（图1）

## 尝试直接对ready打一拍

```verilog
READY_UP <= READY_DOWN;
VALID_DOWN = valid_up;
```

*（仅示例，非verilog代码。下同）*

这样是行不通的。

一个简单的例子（case 1）就是你让READY_DOWN像一个时钟一个，间隔一个cycle起来一次，那么VALID_UP && READY_UP 与 VALID_DOWN && READY_DOWN无法同步，数据无法传输下去。

## 思路：将其分解成两个interfaces

将ready打拍的逻辑想象成一个黑盒子，去分析这个黑盒子的设计，分为up interface 和down interface将问题细化：

- up interface 有VALID_UP, DATA_UP, READY_UP
- down interface 有VALID_DOWN, DATA_DOWN, READY_DOWN
  可以总结成下面的样子：

```verilog
READY_UP <= READY_DOWN; //or READY_UP = function(READY_DOWN_next);
transfer_up = VALID_UP && READY_UP;
transfer_down = VALID_DOWN && READY_DOWN;
```

如果去解决刚才例子（case 1）,那么这个黑盒子：

> 当READY_UP为高的时候，可以接受数据;
> 当READY_DOWN为高的时候，**如果我们有数据可发的话**，我们可以向downstream发送数据;

是不是很像一个FIFO？

# 用FIFO去解决

将一个FIFO插在黑盒子这里，那么就会变成这样子：

![img](https://cdn.jsdelivr.net/gh/dadongshangu/CDN@master/images/20200907_black_box_fifo.JPG)

（图2）

> VALID_UP/READ_YUP ==> FIFO ==> VALID_DOWN/READY_DOWN

也就是:

```verilog
VALID_UP = fifo_push_valid;
READY_UP = fifo_push_ready;
VALID_DOWN = fifo_pop_valid;READY_DOWN = fifo_pop_ready;
```

现在问题变成了：*如何设计这个FIFO呢？*

- 这个FIFO深度多少？
- 怎么设计，能够保证READY_UP是READY_DOWN打过一拍的呢？

## FIFO设计多深？

因为本身valid/ready协议是**反压协议**(*也就是READY_UP为0的时候，不会写FIFO，而不会导致FIFO溢出*)而且此处的读写时钟是同一个时钟，是一个同步FIFO，所以FIFO深度是1或者2就足够了。

深度是1还是2要看极端情况下需要存储几笔数据。

简单分析可以知道，只有一种情况会去向FIFO中存储数据：

- READY_UP是1，可以从upstream接收数据
- 同时READY_DOWN是0，不可以向downstream发送数据

这种情况在极端情况下最多维持多久呢？
**答案是：一个周期**

***
因为如果cycle *a* 时：READY_DOWN=0,那么cycle *a+1*时，READY_UP变为0了，开始反压，所以只用存一个数就够了。



所以设计为一个深度为1的FIFO就可以了。


深度为1的FIFO有很多特点，设计起来比较简单。比如：wr_ptr/rd_ptr始终指向地址0，所以我们可以删掉wr_ptr和rd_ptr，因为是一个常值0。

## 简单的depth-1 FIFO实现

使用depth-1 FIFO传输数据，可以这样设计：

```verilog
// Depth 1 FIFO.
always @(posedge CLK)begin
	if(RESET)     begin    
	fifo_line_valid <= 0;    
	fifo_push_ready <= 1'b0;    
	fifo_data <= {WIDTH{1'b0}};    
	end
	else	begin
    fifo_push_ready <= fifo_pop_ready;
    	if (fifo_push_ready) begin
    		fifo_line_valid <= fifo_push_valid;
    		fifo_data <= DATA_UP;
    		end
    	else	begin
        	if (fifo_pop_valid && fifo_pop_ready)
                fifo_line_valid <= 1'b0;
            else 
            	fifo_line_valid <= fifo_line_valid;
		end
	end
end
assign fifo_push_valid = VALID_UP;
assign fifo_pop_valid = fifo_line_valid;
assign fifo_pop_ready = READY_DOWN;
assign READY_UP = fifo_push_ready;
assign VALID_DOWN = fifo_line_valid;
assign DATA_DOWN = fifo_data;
```

这解决了READY打拍的问题。但是这里有一些可以改进的地方，比如：

- 是不是可以挤掉多于的气泡？
- 在FIFO为空的时候，数据是不是可以直接bypass FIFO？

## 无气泡传输

关于无气泡传输，可以参考上一篇推送（[*握手协议（pvld/prdy或者valid-ready或AXI）中Valid及data打拍技巧*](http://mp.weixin.qq.com/s?__biz=MzIxMjg2ODQxMw==&mid=2247483672&idx=1&sn=62a940a7ec6d84a7da991ab14f4e1d7c&chksm=97becd4aa0c9445cefdab5bb3ec7f8c6400e7ef9702f6369ab88924a5cba118e122a07b17d16&scene=21#wechat_redirect)）。具体的说，就是既然你这里有个深度为1的FIFO了，那么我是不是可以利用起来，放点数据啊……


当READY_DOWN持续是0的时候，READY_UP依然可以有一个cycle去接收一笔数据，把FIFO资源利用起来：

```verilog
fifo_no_push = ~(fifo_push_valid && fifo_push_ready);
fifo_push_ready <= (fifo_pop_ready||(fifo_no_push && ~fifo_line_valid));
```

同样的原因，在RESET情况下，READY_UP可以为1，可以将复位值修改。
那么FIFO穿越呢？

## FIFO穿越

考虑一个特殊情况(case 2)：

*假设READY_DOWN在复位之后始终为1，*

*然后某个时刻开始VALID_UP为1了。*

是不是每个周期，数据都可以直接传下来而不用进入FIFO，即使READY_DOWN打过一拍？

换句话说：***如果READY_UP=1, READY_DOWN=1, FIFO是空的这种情况下，数据可以直通***。

- 上文特殊情况(case 2)，READY_DOWN/READY_UP一直是1，显然可以。
- READY_UP从0到1的跳变：READY_DOWN也会在前一周期有一个从0到1的跳变。在READY_DOWN为0时，有一笔数据存到FIFO里边（无气泡传输）；当READY_DOWN在时刻*a*从0变到1时，READY_UP在时刻*a+1*也会从0变为1。如果此时READY_DOWN也为1，可以直通，不用进入FIFO。也就是：

```
assign pass_through = READY_UP && READY_DOWN && ~fifo_line_valid;
assign VALID_DOWN = pass_through ? VALID_UP : fifo_line_valid;
assign DATA_DOWN = pass_through ? DATA_UP : fifo_data;
```

注意在直通时，我们不希望数据进入FIFO：

```
assign fifo_push_valid = ~pass_through && VALID_UP;
```

## 将所有这些结合起来：

```verilog
//---------------------------------------
// File Name   : ready_flop.v
// Author      : Xiangzhi Meng
// Date        : 2020-06-06
// Version     : 0.1
// Description :
// 1. ready_flop using one depth-1 FIFO to hold data.
//
// All rights reserved.
`timescale 1ns/1ns
module ready_flop
	(
	CLK,
    RESET,
    VALID_UP,
    READY_UP,
    DATA_UP,
    VALID_DOWN,
    READY_DOWN,
    DATA_DOWN
    );
//---------------------------------------
parameter WIDTH            = 32;
//---------------------------------------
input                      CLK;
input                      RESET;
//Up stream
input                      VALID_UP;
output                     READY_UP;
input  [0:WIDTH-1]         DATA_UP;
//Down Stream
output                     VALID_DOWN;
input                      READY_DOWN;
output [0:WIDTH-1]         DATA_DOWN;
//---------------------------------------
wire                       CLK;
wire                       RESET;
//Up stream
wire                       VALID_UP;
wire                       READY_UP;
wire   [0:WIDTH-1]         DATA_UP;
//Down Stream
wire                       VALID_DOWN;
wire                       READY_DOWN;
wire   [0:WIDTH-1]         DATA_DOWN;
reg                        fifo_line_valid;
wire                       fifo_push_valid;
reg                        fifo_push_ready;
wire                       fifo_pop_ready;
wire                       fifo_no_push;
wire                       pass_through;
wire                       fifo_pop_valid;
reg    [0:WIDTH-1]         fifo_data;
// Depth 1 FIFO.
always @(posedge CLK)	begin    
	if(RESET)    begin    
		fifo_line_valid <= 0;
		fifo_push_ready <= 1'b1;    
		fifo_data <= {WIDTH{1'b0}};    
		end    
	else	begin
		fifo_push_ready <= (fifo_pop_ready||(fifo_no_push && ~fifo_line_valid));
		//Bubble clampping: If last cycle there's no FIFO push and
		//fifo_line is empty,it can be ready.
		if (fifo_push_ready)        begin            
			fifo_line_valid <= fifo_push_valid;            
			fifo_data <= DATA_UP;        
		end
		else	begin            
			if (fifo_pop_valid && fifo_pop_ready)
				fifo_line_valid <= 1'b0;            
			else
				fifo_line_valid <= fifo_line_valid;        
		end    
	end
end
assign fifo_no_push = ~(fifo_push_valid && fifo_push_ready);
assign pass_through = READY_UP && READY_DOWN && ~fifo_line_valid;
assign fifo_push_valid = ~pass_through && VALID_UP;
assign fifo_pop_valid = fifo_line_valid;
assign fifo_pop_ready = READY_DOWN;
assign READY_UP = fifo_push_ready;

//bypass
assign VALID_DOWN = pass_through ? VALID_UP : fifo_line_valid;
assign DATA_DOWN = pass_through ? DATA_UP : fifo_data;
endmodule
```
*(注：代码未经详细验证)*

## 换一种思路

经过上面对FIFO的分析，我们可以总结起来，主要是以下几点：

- 加入一个深度为1的同步FIFO，这个FIFO在READY_DOWN为0,且READY_UP为1时暂存一个数据；
- 在READY_DOWN从0->1时，FIFO里边的数据先输出到下级；
- 如果READY_DOWN继续为1，数据可以绕过FIFO直通；

深度为1的FIFO（不管是同步还是异步FIFO），都是一个特殊的逻辑单元。

对于深度为1的同步FIFO，其实就是一拍寄存器打拍。
所以，我们可以这样重新设计：

1. 加一级寄存器作为buffer（实际上就是深度为1的FIFO）
2. 当以下条件满足，这一级寄存器会暂存一级数据：
   2.1 READY_DOWN是0，并且
   2.2 READY_UP是1,并且
   2.3 VALID_UP是1;

也就是：

```verilog
assign store_data = VALID_UP && READY_UP && ~READY_DOWN;
```

1. 当READY_UP是1时,数据可以直接*暴露*在下级接口：READY_UP为1时，BUFFER中一定是空的，因为上一个时钟周期数据已经排空了。也就是:

```verilog
assign VALID_DOWN = READY_UP ? VALID_UP : buffer_valid;
```

这其实就是上面的FIFO直通模式。同样我们可以挤掉气泡：

```verilog
READY_UP <= READY_DOWN || ((~buffer_valid) && (~store_data)); 
```

把这所有的总结起来：

```verilog
//---------------------------------------
// File Name   : ready_flop.v
// Author      : Xiangzhi Meng
// Date        : 2020-06-06
// Version     : 0.1
// Description :
// 1. ready_flop using one buffer to hold data.
//
// All rights reserved.
`timescale 1ns/1ns
module ready_flop        
	(
    CLK,
    RESET,
    VALID_UP,
    READY_UP,
    DATA_UP,
    VALID_DOWN,
    READY_DOWN,
    DATA_DOWN
    );
//---------------------------------------
parameter WIDTH            = 32;
//---------------------------------------
input                      CLK;
input                      RESET;
//Up stream
input                      VALID_UP;
output                     READY_UP;
input  [0:WIDTH-1]         DATA_UP;
//Down Stream
output                     VALID_DOWN;
input                      READY_DOWN;
output [0:WIDTH-1]         DATA_DOWN;
//---------------------------------------
wire                       CLK;
wire                       RESET;
//Up stream
wire                       VALID_UP;
reg                        READY_UP;
wire   [0:WIDTH-1]         DATA_UP;
//Down Stream
wire                       VALID_DOWN;
wire                       READY_DOWN;
wire   [0:WIDTH-1]         DATA_DOWN;
wire                       store_data;
reg    [0:WIDTH-1]         buffered_data;
reg                        buffer_valid;
//---------------------------------------
//buffer.
assign store_data = VALID_UP && READY_UP && ~READY_DOWN;
always @(posedge CLK)
	if (RESET)  buffer_valid <= 1'b0;
	else        buffer_valid <= buffer_valid ? ~READY_DOWN: store_data;
//Note: If now buffer has data, then next valid would be ~READY_DOWN:   
//If downstream is ready, next cycle will be un-valid.    
//If downstream is not ready, keeping high. 
// If now buffer has no data, then next valid would be store_data, 1 for store;
always @(posedge CLK)
	if (RESET)  buffered_data <= {WIDTH{1'b0}};
	else        buffered_data <= store_data ? DATA_UP : buffered_data;

always @(posedge CLK) begin
	if (RESET)  READY_UP <= 1'b1; //Reset can be 1.
	else        READY_UP <= READY_DOWN || ((~buffer_valid) && (~store_data)); //Bubule clampping
	end
//Downstream valid and data.
//Bypass
assign VALID_DOWN = READY_UP? VALID_UP : buffer_valid;
assign DATA_DOWN  = READY_UP? DATA_UP  : buffered_data;
endmodule
```

*(注：代码未经详细验证)*

## 其他

1. 我在电脑上简单跑了两个波形，FIFO方法和Buffer方法结果是一样的。
2. 用FIFO去隔离开上下两个interface思考，比较容易想明白。
3. 无气泡传输、FIFO直通这两个小feature拿掉，也可以工作、也是能实现READY_DOWN时序优化的设计目标的。


---------

电路设计心得，欢迎关注“数字逻辑电路小站”公众号