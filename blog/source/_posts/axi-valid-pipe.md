---
title: 握手协议（pvld/prdy或者valid-ready或AXI）中Valid及data打拍技巧
date: 2020-09-07 22:27:57
tags: verilog
---

## 内容提要

- valid 与data 的时序修复时的打拍
- 如何无气泡？
- 预告：ready修复

## 问题描述

AXI 协议使用的是valid-ready握手的方式去传输数据。关于valid ready 握手，有几个要点：

- 数据data使用valid作为有效性指示。当valid为1是，data数据才有效。

- valid和ready信号同时为高时，数据传输真正发生。

- valid在没有ready到来的情况下，不能自己变为0。也就是，数据没有处理，必须一直等待。

- ready表征下一级是否准备好。ready信号可以随时起来，随时下去。

<!--more-->

![valid_ready](https://cdn.jsdelivr.net/gh//CDN@master/images/20200907_valid_ready.JPG)

## valid与data的时序修复

对于valid 跟data的时序问题，比较好修，这也是pipeline机制中，最常见的修timing的方法：打一拍。所有的打一拍，都可以抽象为valid-ready data 模型。在这个模型中。valid 和data需要打一拍，改善时序。

### 最常见的修复方法

valid在握手的情况下，打一拍，传到下级，不握手的情况下，维持原值。data数据一样。对于ready则是直接传过去即可。

```
VALID_DOWN <= handshake ? VALID_UP : VALID_DOWN         ;
DATA_DOWN  <= handshake ? DATA_UP : DATA_DOWN           ;
READY_UP    = READY_DOWN                                ;
```

### 进行修改——简化

对其进行修改，可以发现逻辑进行简化：valid的逻辑，在传输的时候，可以直接使用ready_up。也就是，ready_up是1的时候，你可以传。也就是变为如下代码：

```
VALID_DOWN <= READY_UP  ? VALID_UP : VALID_DOWN         ;
DATA_DOWN  <= handshake ? DATA_UP : DATA_DOWN           ;
READY_UP    = READY_DOWN                                ;
```

### 进行修改——无气泡传输

对其继续进行修改，可以发现现在的电路，已经存在了一级寄存器。这一级寄存器，可以给上一级的data，多提供一级存储。也就是说，就算是下级ready是0，只要寄存器里边没有数，上一级仍然可以ready为高，将数据存储一拍。本质上就是消除了一级气泡。

```
VALID_DOWN <= READY_UP  ? VALID_UP : VALID_DOWN         ;
DATA_DOWN  <= handshake ? DATA_UP : DATA_DOWN           ;
assign READY_UP = READY_DOWN || ~VALID_DOWN             ;
```

### 示例代码

这是最常用的一个valid打拍的情况。详细示例代码如下，仅供参考：

(p.s.：本代码为业余时间作为个人兴趣写的代码，未经严谨验证，仅供原型原理说明，可复制粘贴使用，但不承诺准确性。)

```
module valid_flop
        (
        CLK                                                                     ,
        RESET                                                                   ,
        VALID_UP                                                                ,
        READY_UP                                                                ,
        DATA_UP                                                                 ,
        VALID_DOWN                                                              ,
        READY_DOWN                                                              ,
        DATA_DOWN
        );

//-----------------------------------------------------------------------------
parameter WIDTH            = 32                                                 ;

//-----------------------------------------------------------------------------
input                      CLK                                                  ;
input                      RESET                                                ;
input                      VALID_UP                                             ;
output                     READY_UP                                             ;
input  [WIDTH-1:0]         DATA_UP                                              ;
output                     VALID_DOWN                                           ;
input                      READY_DOWN                                           ;
output [WIDTH-1:0]         DATA_DOWN                                            ;

//-----------------------------------------------------------------------------
wire                       CLK                                                  ;
wire                       RESET                                                ;
wire                       VALID_UP                                             ;
wire                       READY_UP                                             ;
wire   [WIDTH-1:0]         DATA_UP                                              ;
//Down Stream
reg                        VALID_DOWN                                           ;
wire                       READY_DOWN                                           ;
reg    [WIDTH-1:0]         DATA_DOWN                                            ;

//-----------------------------------------------------------------------------
//Valid
always @(posedge CLK)
if (RESET)  VALID_DOWN <= 1'b0                                                  ;
else        VALID_DOWN <= READY_UP ? VALID_UP : VALID_DOWN                      ;
//Data
always @(posedge CLK)
if (RESET)  DATA_DOWN <= {WIDTH{1'b0}}                                          ;
else        DATA_DOWN <= (READY_UP && VALID_UP) ? DATA_UP : DATA_DOWN           ;
//READY with buble collapsing.

assign READY_UP = READY_DOWN || ~VALID_DOWN                                     ;
//READY with no buble collapsing.

//assign READY_UP = READY_DOWN                                                  ;

endmodule
```

### 模型变化

上面的模型可以有很多变化，比如一种协议，不存在反压，或者说只有valid 和data，数据总是可以发送的。

```
VALID_DOWN <= VALID_UP        							;
DATA_DOWN  <= VALID_UP ? DATA_UP : DATA_DOWN            ;
valid only_no_data模型
```

上面的模型继续变化，比如只有control信号，没有数据(data)。就简化成直接打一拍了。

```
VALID_DOWN <= VALID_UP        							;
```

## 下节预告

valid ready 协议中对ready进行timing 修复打拍的方法。