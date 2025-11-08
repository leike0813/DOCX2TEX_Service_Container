

# **XML Calabash 命令行调用语法综合分析报告**

## **I. 引言：关键的版本区别 (1.x 与 3.x)**

XML Calabash 是 W3C XProc 规范的核心实现之一 1。在调研其命令行语法时，必须首先明确一个至关重要的事实：XML Calabash 没有统一的命令行语法。其语法存在一个根本性的“版本鸿沟”，即 1.x 版本系列和 3.x 版本系列。

这种差异并不仅仅是参数的增减，而是彻底的重新设计。3.x 版本被明确描述为针对 XProc 3.0 规范的“完整重新实现” 2。因此，1.x 版本的文档已被官方归档，并明确警告访问者“这些不是您要查找的网页”，引导用户转向 3.x 的最新内容 2。

这种语法的演变直接反映了 XProc 规范自身的发展：

* **1.x 语法 (遗留)：** 如 java com.xmlcalabash.drivers.Main \-s p:xslt... 3 所示，它反映了一种早期的、更偏向于“调用 Java 类”和即时构建简单步骤链的模式。  
* **3.x 语法 (现代)：** 如 xmlcalabash run pipeline.xpl... 5 所示，它演变为一个功能齐全的、命令驱动的应用程序接口，具有用于诊断 (info) 和执行 (run) 的独立子系统，以支持 XProc 3.0 更成熟和复杂的生态系统。

GitHub 上的代码库也证实了这种分离，存在 xmlcalabash1 6 和 xmlcalabash3 7 两个独立的项目（以及一个短暂的 xmlcalabash2 8）。

**本报告将以 3.x 版本的语法作为当前标准进行详尽分析，并将 1.x 语法作为遗留参考独立呈现。** 混淆这两个版本的语法将导致调用彻底失败。

## **II. XML Calabash 3.x 命令行架构深度分析**

XML Calabash 3.x 采用了现代化的、命令驱动的命令行界面 5。

### **基本调用方式**

有两种主要方式来启动 3.x 版本的 XML Calabash：

1. 通过 JAR 文件（推荐）：  
   java \-jar xmlcalabash-3.0.x.jar \[命令\]\[选项...\] 5  
2. 通过主类：  
   java com.xmlcalabash.app.Main \[命令\]\[选项...\] 5

值得注意的是，3.x 的主类路径 (com.xmlcalabash.app.Main) 不同于 1.x 的路径 (com.xmlcalabash.drivers.Main) 3，这再次印证了其作为完全重写的性质。在后续示例中，我们将假设 xmlcalabash 是上述命令的别名（如官方文档所建议）以便于阅读 5。

### **命令驱动的界面**

3.x 的语法结构是 xmlcalabash \[命令\]\[选项...\]。它支持三个核心命令 5：

* run: 执行一个 XProc 管道。  
* info: 打印诊断和环境信息。  
* help: 显示帮助摘要。

一个关键的易用性设计是：**如果未提供任何命令，run 命令将被作为默认命令** 5。这意味着 1.x 版本的用户如果尝试 xmlcalabash my-pipeline.xpl，该命令仍能成功执行，因为系统会自动假定用户意图是 xmlcalabash run my-pipeline.xpl。这种设计巧妙地保留了与旧版本相似的“感觉”，降低了迁移的门槛。

## **III. XML Calabash 3.x：辅助命令分析 (help 与 info)**

help 和 info 命令提供了关键的诊断功能，对于成功的管道开发和故障排除至关重要。

### **help 命令**

help 命令用于显示命令行选项和参数的简短摘要 5。

* **语法：** xmlcalabash help  
* **行为：** 如果请求了 help，所有其他命令行参数都将被忽略。在 run 命令上使用 \--help 选项与执行 help 命令具有同等效果 5。

### **info 命令**

info 命令本身不是一个单一命令，而是用于诊断的子命令命名空间 5。

#### **info version**

此命令显示 XML Calabash 及其关键依赖（如 Saxon）的版本信息 5。

* **语法：** xmlcalabash info version \[--verbosity:level\]\[--debug\]  
* **标准输出：** 默认情况下，它会打印 XML Calabash 和 Saxon 的版本号 5。  
* **详细输出：** 如果提供了 \--verbosity:debug，版本摘要将包含有关第三方依赖项（如 HTML 解析器和 XML 解析器）的详细信息，并以易于解析的格式输出 5。

#### **info mimetypes**

此命令显示所有已注册的 MIME 类型（内容类型）。

* **语法：** xmlcalabash info mimetypes  
* **输出：** 它会列出所有通过默认配置、用户配置文件和扩展步骤注册的 MIME 类型 5。

#### **info mimetype \[extension\]**

此命令返回特定文件扩展名的内容类型信息。

* **语法：** xmlcalabash info mimetype.xml  
* **输出：** 它将报告以 .\[extension\] 结尾的文件（或 URI）将被解析为什么内容类型 5。

info mimetypes 和 info mimetype 这两个命令的实用性远超简单的信息显示。它们构成了一个关键的“诊断循环”。run 命令的 \--input 选项（将在第五节中详述）依赖于正确推断文件的内容类型 5。如果未明确指定类型，XML Calabash 会尝试根据 URI 自动推断 5。如果推断错误，管道将失败。此时，info mimetypes 和 info mimetype.ext 就是用户必须使用的工具，用以诊断为什么 Calabash 会为某个特定输入文件选择错误的解析方式。

## **IV. 核心分析：XML Calabash 3.x run 命令**

run 命令是 XML Calabash 的核心功能，用于执行 XProc 管道。其语法结构非常灵活，可以分为几个关键部分。

完整语法概要（5）：  
xmlcalabash \[run\]\[通用选项...\]\[管道文件\]\[管道特定选项...\]

### **第 1 部分：管道与步骤规范**

有三种主要方式来指定要执行的操作：

1. 运行 .xpl 管道文件：  
   这是最常见用法。xmlcalabash pipeline.xpl。如果该文件的根元素是 \<p:declare-step\>，则该管道将被运行 5。  
2. 从库中运行特定步骤：  
   如果 .xpl 文件是一个包含 \<p:library\> 的库，可以使用 \--step 选项指定要运行该库中的哪个步骤 5。  
   * **语法：** xmlcalabash \--step:step-name my-library.xpl  
   * **说明：** my-library.xpl 必须是一个库文件，--step 的值是该库中定义的步骤*名称* 5。  
3. 运行单个原子步骤：  
   当未指定 .xpl 管道文件时，--step 选项的含义会发生变化：它允许用户直接运行一个原子步骤（Atomic Step）5。  
   * **语法：** xmlcalabash \--step:p:xslt \[输入/输出/选项...\]  
   * **说明：** 此时，--step 的值是步骤的*类型*（例如 p:xslt 或 p:validate-with-xml-schema）。所有其他输入、输出和选项都将应用于这个单独的步骤 5。

这种“运行原子步骤”的模式 5，实质上是 1.x 版本中 \-s 标志 3 的“精神继承者”。两者都服务于同一个目的：在不需要编写完整 .xpl 文件的情况下，快速执行简单的、线性的 XML 操作。对于从 1.x 迁移的用户来说，这是一个关键的对应点。

### **第 2 部分：高级配置与调试选项**

run 命令接受一系列通用选项来控制执行环境：

* \--configuration:file: 指定一个配置文件。如果未指定，XML Calabash 会自动在当前目录和用户主目录中查找 .xmlcalabash3 文件 5。  
* \--debug: 启用调试模式。这会将日志级别至少设置为 "debug"，并保留用于生成图表等的中间文件 5。  
* \--verbosity:level: 控制管道运行时打印的进度信息量。它同时也设置了日志记录级别 5。

| 表 1：XML Calabash 3.x Verbosity (详细程度) 级别 |
| :---- |
| **级别** |
| trace |
| debug |
| info |
| warn |
| error |

* \--trace:output-file 和 \--trace-documents:output-dir: 启用高级执行跟踪，用于深度管道分析 5。  
* \--debugger: 启动交互式调试器 5。  
* \--extension:name: 启用一个命名的扩展 5。  
* \--init:class-name: 加载并执行一个 Saxon 配置初始化类（必须实现 net.sf.saxon.lib.Initializer 接口）5。

## **V. 深度分析：输入与输出绑定 (3.x run)**

run 命令使用 \--input 和 \--output 选项将数据传入和传出 XProc 管道定义的端口。

### **输入端口绑定 (--input)**

\--input 选项用于将文档资源绑定到管道的输入端口 5。

* **语法：** \--input:\[type@\]port=uri  
* **port：** 必须是管道中定义的输入端口的名称（例如 source）。  
* **uri：** 资源的 URI（例如 file.xml, http://example.com/doc.xml）。  
* **标准输入 (stdin)：** 如果 uri 是一个单独的连字符 (-)，输入将从标准输入流中读取 5。  
* **文档序列：** 如果对*同一个端口*多次使用 \--input 选项（例如 \--input:source=a.xml \--input:source=b.xml），这些文档将按顺序组合成一个*文档序列*，并馈送到该端口 5。  
* **\[type@\] 前缀：**  
  * 这是一个可选项，用于*强制*指定输入内容的 MIME 类型（例如 application/xml@）5。  
  * 如果省略，XML Calabash 会尝试从 uri（例如文件扩展名）*推断*内容类型。  
  * 在从 stdin (-) 读取时，如果未提供 type，系统将尝试使用该端口上声明的第一个“可用”内容类型，如果端口没有指定类型，则默认为 XML 5。

### **输出端口绑定 (--output)**

\--output 选项决定了管道输出端口上的文档如何被存储 5。

* **语法：** \--output:port=filespec  
* **port：** 必须是管道中定义的输出端口的名称。如果省略，则假定为*主输出端口* 5。  
* **filespec：** 文件规范。  
* **标准输出 (stdout)：** 如果 filespec 是一个单独的连字符 (-)，输出将写入标准输出流。最多只能有一个输出端口被显式绑定到 stdout 5。

#### **filespec 与序列处理**

filespec 的设计必须解决一个关键问题：当一个输出端口产生*多个*文档时会发生什么？

* 解决方案 1：连接 (Concatenation)  
  如果 filespec 是一个简单的文件名（例如 out.xml），那么该端口上的所有输出文档将被连接（concatenate）并写入到同一个文件中 5。这对于 XML 输出通常会导致文件格式错误（例如，多个 XML 声明或多个根元素）。  
* 解决方案 2：模板 (Template)  
  为了正确处理序列，filespec 可以是一个包含编号模板的字符串 5：  
  * %d: 替换为文档编号 (从 1 开始)。  
  * %x: 替换为十六进制编号。  
  * %o: 替换为八进制编号。  
  * **格式化：** 可以在 % 和格式说明符之间指定宽度，例如 %02d 会产生至少两位数的编号，不足则在左侧补 0（例如 01, 02...）。  
  * **字面量：** %% 用于在文件名中插入一个字面量的 % 5。

#### **标准输出 (stdout) 的隐患**

stdout 的行为比看起来要复杂。5 描述了一种复杂的逻辑，该逻辑依赖于 \--pipe 选项以及 stdout 是否连接到终端。如果 stdout 似乎正在写入终端窗口，Calabash 可能会添加“装饰”（decoration），例如用于标识端口名称和文档编号的页眉，以及文档之间的分隔符（=行）5。

这种“装饰”对于人类在终端上阅读是友好的，但对于脚本处理却是灾难性的。这意味着 xmlcalabash... \> my-file.xml 可能会产生一个与 xmlcalabash... \--output:result=my-file.xml *不同*的（并且可能已损坏的）文件。

因此，为了获得可预测的、健壮的、可用于脚本的输出，**必须始终使用显式的 \--output:port=filespec 或 \--output:port=- 绑定**，而绝不应依赖于对多端口管道的隐式 stdout 重定向。

## **VI. 深度分析：参数、选项与命名空间 (3.x run)**

这是 3.x 命令行语法中最复杂但功能最强大的部分：如何将简单的值（而不是文档）传递给管道。

### **第 1 部分：命名空间绑定 (--namespace)**

在 XProc 中，选项和参数通常使用 QNames（带前缀的名称）。--namespace 选项用于在命令行上定义这些前缀 5。

* **语法：** \--namespace:prefix=uri (例如：--namespace:my=http://example.com)  
* **用途：** 定义的绑定可用于 option=value 和 \!serialparam=value 表达式中。  
* **默认绑定：** XML Calabash 会自动提供一组默认的命名空间绑定 5。

| 表 2：XML Calabash 3.x 默认命名空间前缀 |
| :---- |
| **前缀** |
| array |
| cx |
| fn |
| map |
| math |
| p |
| saxon |
| xs |

### **第 2 部分：管道选项 (option=value)**

这些参数用于设置管道中声明的 \<p:option\> 的值。它们必须出现在管道文件名*之后* 5。

* **字面字符串：**  
  * **语法：** option-name=value  
  * **行为：** 整个 value 字符串作为 xs:untypedAtomic 类型的值传递 5。  
* **XPath 表达式：**  
  * **语法：** option-name=?expression  
  * **行为：** 关键在于 ? 前缀。? 之后的所有内容都将被视为 XPath 表达式进行求值。求值结果（可以是原子值、序列、map 等）将成为选项的值 5。  
  * **示例：** my-bool=?'true' cast as xs:boolean 或 my-seq=?(1, 2, 3)。  
  * **命名空间：** 可以在 XPath 中使用 \--namespace 定义的前缀或默认前缀。  
* **Map 语法：**  
  * **语法：** map-option::key=value  
  * **行为：** 用于设置值为 map 的选项中的特定条目 5。

### **第 3 部分：序列化参数 (\!serialparam=value)**

这些参数*不*传递给管道，而是用于*控制*输出端口如何将 XML（或 JSO、Text）序列化为字节流 5。

* **语法（主端口）：** \!param=value (例如 \!indent=true)  
  * **行为：** 应用于*主输出端口* 5。  
* **语法（特定端口）：** port-name::\!param=value (例如 secondary-port::\!method=text)  
  * **行为：** 应用于名为 port-name 的特定端口 5。  
* **值：** 同样，可以使用 ? 前缀通过 XPath 表达式提供值（例如 \!indent=?'true' cast as xs:boolean）5。

#### **关键陷阱：\! 前缀的缺失**

option=value 和 \!serialparam=value 之间的区别是极其重要且容易出错的。唯一的区别就是感叹号 \! 5。

* \!indent=true：**序列化参数**。指示 Calabash 在序列化*主输出端口*时启用缩进。  
* indent=true：**管道选项**。将一个名为 indent 的*选项*（值为字符串 "true"）传递给管道。

如果用户想要缩进输出，但错误地输入了 indent=true（忘记了 \!），将*不会*发生错误。Calabash 会默默地将一个可能无用的 indent 选项传递给管道，而输出*仍将*不被缩进，导致用户困惑。这是 3.x 语法中最常见的用户错误来源之一。

| 表 3：3.x run 命令值语法总结 |
| :---- |
| **目的** |
| 输入文档 |
| 来自 Stdin 的输入 |
| 管道选项 (字符串) |
| 管道选项 (XPath) |
| 序列化 (主端口) |
| 序列化 (特定端口) |

## **VII. 遗留系统参考：XML Calabash 1.x 语法**

对于维护遗留系统（例如 XML 编辑器中的旧集成 11）的用户，了解 1.x 语法仍然是必要的。

### **基本调用方式**

1.x 版本通过直接调用 Java 主类来运行 3：  
java com.xmlcalabash.drivers.Main \[选项\] pipeline.xpl

### **输入和输出标志**

1.x 使用简短的标志来绑定端口 3：

* \-i port=file: 绑定一个文件到输入端口。  
  * 示例：-isource=doc.xml  
* \-o port=file: 绑定一个输出端口到一个文件。  
  * 示例：-oresult=/tmp/out.xml

### **命令行管道构建 (-s)**

1.x 语法最独特的特性是使用 \-s 标志在命令行上动态构建管道 2。这允许用户在没有 .xpl 文件的情况下链式执行步骤。

* **语法：** \-s steptype  
* **行为：** 在 \-s 标志*之前*提供的任何 \-i（输入）或参数标志都将应用于*该*步骤。  
* **示例 1 (XSLT)：**  
  Bash  
  java com.xmlcalabash.drivers.Main \\  
       \-isource=doc.xml \\  
       \-istylesheet=style.xsl \\  
       \-s p:xslt

  3  
* **示例 2 (验证后跟 XSLT)：**  
  Bash  
  java com.xmlcalabash.drivers.Main \\  
       \-isource=doc.xml \\  
       \-ischema=schema.xsd \\  
       \-s p:validate-with-xml-schema \\  
       \-istylesheet=style.xsl \\  
       \-s p:xslt

  3

这种机制 3 之所以有效，是因为它“通过在命令行上传递的步骤构建了一个字面意义的管道”。它假定前一个步骤（p:validate-with-xml-schema）的主输出会*隐式*连接到下一个步骤（p:xslt）的主输入 (source)。这种模型对于简单的线性链条非常有效，但一旦需要非主端口绑定、分支或复杂逻辑，该模型就会立即失效。这也从根本上解释了为什么需要 XProc 语言本身以及功能更强大的 3.x 运行器。

## **VIII. 综合与结论性建议**

### **语法综合**

对 XML Calabash 命令行语法的调查显示，1.x 和 3.x 版本之间存在根本性的、不可兼容的差异。这种差异是 XProc 规范从 1.0 演进到 3.0 的直接反映。

* **1.x (遗留)：** 是一个 Java 类调用，使用 \-i, \-o 和 \-s 标志，擅长构建简单的线性步骤链。  
* **3.x (现代)：** 是一个功能齐全的应用程序，具有 run, info, help 子命令。其 run 语法严格区分了：  
  1. **文档输入** (--input)  
  2. **管道选项** (option=value)  
  3. **序列化参数** (\!param=value)

下表总结了从 1.x 迁移到 3.x 的关键语法变化：

| 表 4：1.x 到 3.x 语法迁移指南 |
| :---- |
| **任务** |
| 运行管道 |
| 指定输入 |
| 指定输出 |
| 指定选项 |
| 运行简单 XSLT |
| 更改输出缩进 |

### **结论性建议**

基于本次分析，向 XML Calabash 用户提供以下操作建议：

1. **仅使用 3.x：** 对于所有新项目，应*仅*使用 3.x 语法，并参考 3.x 文档。所有 1.x 文档 2 都应被视为已归档的遗留参考。  
2. **识别遗留系统：** 如果维护现有系统，请立即通过检查调用方式（...drivers.Main vs ...app.Main）或语法（-s vs \--step）来确定版本。  
3. **调试 3.x 选项：** 在 3.x 中，最常见的错误来源是混淆 option=value（管道参数）和 \!serialparam=value（序列化控制）5。在调试序列化问题（如缩进、方法）时，请务必检查 \! 是否存在。  
4. **调试 3.x 输入：** 如果 3.x 管道因内容类型错误而失败，请使用 info mimetypes 和 info mimetype.ext 5 来诊断 Calabash 的类型推断，并使用 \--input:type@port=uri 语法（例如 \--input:application/xml@source=in.doc）来显式覆盖它 5。  
5. **编写 3.x 脚本：** 为了在自动化脚本中获得可靠的输出，**必须**使用 \--output:port=filespec 或 \--output:port=- 显式绑定*所有*预期的输出端口。切勿依赖隐式的 stdout 重定向，以避免潜在的“装饰”内容导致输出损坏 5。

#### **Works cited**

1. XML Calabash: an XProc implementation \- Norman Walsh, accessed November 8, 2025, [https://norman.walsh.name/2008/projects/calabash](https://norman.walsh.name/2008/projects/calabash)  
2. Welcome to XML Calabash (1.0), accessed November 8, 2025, [https://www.xmlcalabash.com/archive-1.x/](https://www.xmlcalabash.com/archive-1.x/)  
3. Documentation \- XML Calabash, accessed November 8, 2025, [https://www.xmlcalabash.com/archive-1.x/docs/](https://www.xmlcalabash.com/archive-1.x/docs/)  
4. 2\. The command line \- XML Calabash, accessed November 8, 2025, [https://www.xmlcalabash.com/archive-1.x/docs/reference/cmdline.html](https://www.xmlcalabash.com/archive-1.x/docs/reference/cmdline.html)  
5. Chapter 2\. Running XML Calabash \- XML Calabash Documentation, accessed November 8, 2025, [https://docs.xmlcalabash.com/userguide/current/running.html](https://docs.xmlcalabash.com/userguide/current/running.html)  
6. ndw/xmlcalabash1: XML Calabash, an XProc processor \- GitHub, accessed November 8, 2025, [https://github.com/ndw/xmlcalabash1](https://github.com/ndw/xmlcalabash1)  
7. xmlcalabash/xmlcalabash3: XML Calabash 3.x, an implementation of XProc 3.x \- GitHub, accessed November 8, 2025, [https://github.com/xmlcalabash/xmlcalabash3](https://github.com/xmlcalabash/xmlcalabash3)  
8. ndw/xmlcalabash2: XML Calabash V2 \- GitHub, accessed November 8, 2025, [https://github.com/ndw/xmlcalabash2](https://github.com/ndw/xmlcalabash2)  
9. XML Calabash User Guide, accessed November 8, 2025, [https://docs.xmlcalabash.com/userguide/3.0.22/](https://docs.xmlcalabash.com/userguide/3.0.22/)  
10. XML Calabash User Guide, accessed November 8, 2025, [https://docs.xmlcalabash.com/userguide/3.0.21/](https://docs.xmlcalabash.com/userguide/3.0.21/)  
11. XProc: pipelines for project management \- Digital humanities, accessed November 8, 2025, [http://dh.obdurodon.org/xproc-tutorial.xhtml](http://dh.obdurodon.org/xproc-tutorial.xhtml)