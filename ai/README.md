### 250121 AI test function

npm i @langchain/openai @langchain/core @langchain/community pdf-parse

conda activate trpg

npm run dev

[llm direct connect to db](https://js.langchain.com/docs/tutorials/sql_qa/)

[agent overview for ref](https://lilianweng.github.io/posts/2023-06-23-agent/)


以玛丽为例

玛丽·雷克，19岁
STR 40  CON 50  SIZ 45  INT 80  POW 50
DEX 70 APP 60  EDU 85  HP: 9  DB: 0
Build: 0 Move: 8  Sanity 50
攻击: 1
拳击 25% (12/5), 伤害 1D3
.22 左轮枪  35% (17/7), 伤害 1D6 (开局时放在收银台里，而不是自己身上)
闪躲 35% (17/7)
技能: 艺术/手艺(素描) 40%, 魅力 80%, 攀爬40%, 急救 35%, 聆听 50%, 劝服 50%, 心理学 40%, 巧妙手法 40%, 侦查 30%, 潜行 35%.
背景故事
人物介绍：运动员般的健美身体，一米五左右的个子，干练的淡金色短发。
世界观/信念：保全自己重于一切
重要的人：克莱姆·泰勒，她的男友（或许是她离开“这个垃圾场”的门票）
性格特质：警惕、狡猾、工于心计 

————————————————————————————————————————————

技能值后面的括号里的两个数字(例如12/5)分别代表：

1. 第一个数字(12)是技能值的一半，也称为"困难成功"值
2. 第二个数字(5)是技能值的五分之一，也称为"极难成功"值

所以对于拳击技能25%来说：

- 普通成功需要掷骰结果≤25
- 困难成功需要掷骰结果≤12
- 极难成功需要掷骰结果≤5

这是游戏中用来判定行动难度的机制。越困难的情况下，需要掷出更小的数字才能成功。这也体现了即使是熟练的技能，在极端情况下也可能会失败的现实感。

比如在你给出的属性卡中，左轮枪技能35%(17/7)意味着：

- 普通射击需要≤35才成功
- 困难射击(如远距离)需要≤17才成功
- 极难射击(如在剧烈移动时)需要≤7才成功

技能: 艺术/手艺(素描) 40%, 魅力 80%, 攀爬40%, 急救 35%, 聆听 50%, 劝服 50%, 心理学 40%, 巧妙手法 40%, 侦查 30%, 潜行 35%.这些技能的检定也是一样


// ai/rag/loader.js

const { PDFLoader } = require("@langchain/community/document_loaders/fs/pdf");
const { RecursiveCharacterTextSplitter } = require("@langchain/textsplitters");

// load docs
const mechanismLoader = new PDFLoader("../../ai/rag/mechanism.pdf");
const mechanism = await mechanismLoader.load();
console.log(mechanism[0]);
console.log(`Total characters: ${mechanism[0].pageContent.length}`);
// split docs
const splitter = new RecursiveCharacterTextSplitter({
    chunkSize: 1000,
    chunkOverlap: 200,
});
const mechanismChunks = await splitter.splitDocuments(mechanism);
console.log(`Split blog post into ${allSplits.length} sub-documents.`);
// store docs
await vectorStore.addDocuments(allSplits);


const { OpenAIEmbeddings } = require("@langchain/embeddings/openai");
const { Chroma } = require("@langchain/vectorstores/chroma");
const { RetrievalQAChain } = require("@langchain/chains");
// 初始化嵌入模型
const embeddings = new OpenAIEmbeddings({
    openAIApiKey: process.env.OPENAI_API_KEY,
});
  
// 创建向量存储
const vectorStore = await Chroma.fromDocuments(
    ...mechanismChunks,
    embeddings
);
const retriever = vectorStore.asRetriever();
const ragChain = RetrievalQAChain.fromLLM(llm, retriever);



// loadMechanism().catch(console.error);