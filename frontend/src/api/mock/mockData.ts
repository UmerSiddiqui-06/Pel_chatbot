import type { Conversation } from "../../types/chat";

export const seedConversations: Conversation[] = [
  {
    id: "c1",
    title: "Warranty Policy",
    updatedAt: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
    messages: [
      {
        id: "m1",
        role: "user",
        text: "What's the warranty period for the CoolPro AC?",
        createdAt: new Date(Date.now() - 1000 * 60 * 31).toISOString(),
      },
      {
        id: "m2",
        role: "assistant",
        text: "The warranty period for the CoolPro AC is two years from the date of purchase, covering the compressor and major components, according to the available PEL documentation.",
        sources: [{ title: "Warranty Policy", page: 4 }],
        createdAt: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
      },
    ],
  },
  {
    id: "c2",
    title: "Leave Policy",
    updatedAt: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString(),
    messages: [
      {
        id: "m3",
        role: "user",
        text: "How many annual leaves do confirmed employees get?",
        createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString(),
      },
      {
        id: "m4",
        role: "assistant",
        text: "Confirmed employees are entitled to 18 annual leave days per calendar year, as outlined in the Employee Leave Policy.",
        sources: [
          { title: "Employee Leave Policy", page: 6 },
          { title: "HR Procedures Manual", section: "Annual Leave" },
        ],
        createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString(),
      },
    ],
  },
  {
    id: "c3",
    title: "Product Info",
    updatedAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 3).toISOString(),
    messages: [
      {
        id: "m5",
        role: "user",
        text: "What categories of products does PEL manufacture?",
        createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 3).toISOString(),
      },
      {
        id: "m6",
        role: "assistant",
        text: "Based on the available PEL documentation, product records include categories such as air conditioners, refrigerators, and home appliances, each with model-level specification sheets.",
        sources: [{ title: "Product Database", section: "Category Index" }],
        createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 3).toISOString(),
      },
    ],
  },
];
