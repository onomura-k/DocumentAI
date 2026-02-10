#!/usr/bin/env python3
"""
実用的なハイブリッド解決策: OCR Processor + Layout Parser
- OCR Processor (d784f2907961b8a6): 詳細座標・テキスト (1,198文字・161座標)
- Layout Parser (6af87434352688a1): 高度構造分析・チャンキング (6チャンク)
"""

import json
from google.cloud import documentai_v1beta3 as documentai

class PracticalHybridProcessor:
    def __init__(self):
        """実用的なハイブリッドプロセッサ初期化"""
        self.project_id = "gen-lang-client-0849825641"
        self.location = "us"
        self.ocr_processor_id = "d784f2907961b8a6"      # 検出されたOCR Processor
        self.layout_processor_id = "6af87434352688a1"    # Layout Parser
        
        self.client = documentai.DocumentProcessorServiceClient()
    
    def process_document_complete(self):
        """完全なハイブリッド文書処理"""
        print("🔍 実用的ハイブリッド処理開始")
        print("=" * 60)
        
        pdf_file = "sample.pdf"
        with open(pdf_file, "rb") as pdf:
            pdf_content = pdf.read()
        
        print(f"📁 PDF読み込み: {pdf_file} ({len(pdf_content)} bytes)")
        
        raw_document = documentai.RawDocument(
            content=pdf_content,
            mime_type="application/pdf"
        )
        
        # 1. OCR Processorで詳細座標・テキスト情報を取得
        print(f"\n🔍 Step 1: OCR Processor処理")
        ocr_result = self._process_with_ocr(raw_document)
        
        # 2. Layout Parserで構造分析・チャンキングを実行
        print(f"🔍 Step 2: Layout Parser処理")
        layout_result = self._process_with_layout_parser(raw_document)
        
        # 3. 結果を統合・保存
        print(f"🔍 Step 3: 結果統合・保存")
        merged_result = self._merge_and_save_results(ocr_result, layout_result)
        
        return merged_result
    
    def _process_with_ocr(self, raw_document):
        """OCR Processorで詳細座標・テキスト処理"""
        processor_name = f"projects/{self.project_id}/locations/{self.location}/processors/{self.ocr_processor_id}"
        
        request = documentai.ProcessRequest(
            name=processor_name,
            raw_document=raw_document
        )
        
        print("   🚀 OCR Processor実行中...")
        result = self.client.process_document(request=request)
        document = result.document
        
        # OCR結果分析
        bbox_count = 0
        text_length = len(document.text) if document.text else 0
        pages_count = len(document.pages) if hasattr(document, 'pages') else 0
        
        if hasattr(document, 'pages') and document.pages:
            for page in document.pages:
                if hasattr(page, 'blocks') and page.blocks:
                    for block in page.blocks:
                        if hasattr(block, 'layout') and block.layout and hasattr(block.layout, 'bounding_poly') and block.layout.bounding_poly:
                            if hasattr(block.layout.bounding_poly, 'normalized_vertices') and block.layout.bounding_poly.normalized_vertices:
                                bbox_count += 1
        
        print(f"   ✅ OCR Processor完了: {text_length}文字, {bbox_count}座標, {pages_count}ページ")
        return document
    
    def _process_with_layout_parser(self, raw_document):
        """Layout Parserで高度構造分析処理"""
        processor_name = f"projects/{self.project_id}/locations/{self.location}/processors/{self.layout_processor_id}"
        
        process_options = documentai.ProcessOptions(
            layout_config=documentai.ProcessOptions.LayoutConfig(
                chunking_config=documentai.ProcessOptions.LayoutConfig.ChunkingConfig(
                    chunk_size=500,
                    include_ancestor_headings=True
                ),
                return_images=True,
                return_bounding_boxes=True,
                enable_image_annotation=True,
                enable_image_extraction=True,
                enable_table_annotation=True,
                enable_llm_layout_parsing=True
            )
        )
        
        request = documentai.ProcessRequest(
            name=processor_name,
            raw_document=raw_document,
            process_options=process_options
        )
        
        print("   🚀 Layout Parser実行中...")
        result = self.client.process_document(request=request)
        document = result.document
        
        # Layout Parser結果分析
        chunks_count = 0
        if hasattr(document, 'chunked_document') and document.chunked_document:
            chunks_count = len(document.chunked_document.chunks)
        
        blocks_count = 0
        if hasattr(document, 'document_layout') and document.document_layout:
            blocks_count = len(document.document_layout.blocks)
        
        print(f"   ✅ Layout Parser完了: {chunks_count}チャンク, {blocks_count}ブロック")
        return document
    
    def _merge_and_save_results(self, ocr_document, layout_document):
        """OCRとLayout Parserの結果を統合して保存"""
        
        # 統合結果の構築
        merged_result = {
            "timestamp": "2026-02-09",
            "processor": "Practical Hybrid: OCR + Layout Parser",
            "processing_strategy": {
                "ocr_processor": {
                    "id": self.ocr_processor_id,
                    "name": "doc-ocr-test", 
                    "purpose": "詳細座標・テキスト抽出",
                    "results": {
                        "text_length": len(ocr_document.text) if ocr_document.text else 0,
                        "pages_count": len(ocr_document.pages) if hasattr(ocr_document, 'pages') else 0,
                        "coordinates_available": True
                    }
                },
                "layout_parser": {
                    "id": self.layout_processor_id,
                    "name": "Layout Parser v1beta3",
                    "purpose": "構造分析・チャンキング",
                    "results": {
                        "chunks_count": len(layout_document.chunked_document.chunks) if hasattr(layout_document, 'chunked_document') and layout_document.chunked_document else 0,
                        "blocks_count": len(layout_document.document_layout.blocks) if hasattr(layout_document, 'document_layout') and layout_document.document_layout else 0,
                        "llm_parsing_active": True
                    }
                }
            },
            "hybrid_benefits": [
                "✅ 詳細な座標情報 (OCR Processor)",
                "✅ 完全なテキスト抽出 (OCR Processor)", 
                "✅ 高度な構造分析 (Layout Parser)",
                "✅ セマンティックチャンキング (Layout Parser)",
                "✅ LLMベースレイアウト解析 (Layout Parser)"
            ]
        }
        
        # OCR詳細座標情報
        ocr_coordinates = []
        if hasattr(ocr_document, 'pages') and ocr_document.pages:
            for page_idx, page in enumerate(ocr_document.pages):
                if hasattr(page, 'blocks') and page.blocks:
                    for block_idx, block in enumerate(page.blocks):
                        if hasattr(block, 'layout') and block.layout and hasattr(block.layout, 'bounding_poly') and block.layout.bounding_poly:
                            bbox = block.layout.bounding_poly
                            if hasattr(bbox, 'normalized_vertices') and bbox.normalized_vertices:
                                vertices = []
                                for vertex in bbox.normalized_vertices:
                                    vertices.append({
                                        "x": getattr(vertex, 'x', 0),
                                        "y": getattr(vertex, 'y', 0)
                                    })
                                
                                # テキスト内容も取得
                                text_content = ""
                                if hasattr(block, 'layout') and block.layout and hasattr(block.layout, 'text_anchor') and block.layout.text_anchor:
                                    if hasattr(block.layout.text_anchor, 'text_segments') and block.layout.text_anchor.text_segments:
                                        for segment in block.layout.text_anchor.text_segments:
                                            start_idx = getattr(segment, 'start_index', 0)
                                            end_idx = getattr(segment, 'end_index', 0)
                                            if ocr_document.text:
                                                text_content += ocr_document.text[start_idx:end_idx]
                                
                                ocr_coordinates.append({
                                    "page": page_idx + 1,
                                    "block": block_idx + 1,
                                    "coordinates": vertices,
                                    "text": text_content,
                                    "text_length": len(text_content)
                                })
        
        merged_result["ocr_detailed_coordinates"] = ocr_coordinates[:10]  # 最初の10個のサンプル
        merged_result["ocr_coordinates_summary"] = {
            "total_coordinates": len(ocr_coordinates),
            "sample_count": min(10, len(ocr_coordinates))
        }
        
        # Layout Parser チャンク詳細
        layout_chunks = []
        if hasattr(layout_document, 'chunked_document') and layout_document.chunked_document:
            for i, chunk in enumerate(layout_document.chunked_document.chunks):
                chunk_content = getattr(chunk, 'content', '')
                
                layout_chunks.append({
                    "chunk_id": i + 1,
                    "content": chunk_content,
                    "content_length": len(chunk_content),
                    "preview": chunk_content[:200] + "..." if len(chunk_content) > 200 else chunk_content
                })
        
        merged_result["layout_parser_chunks"] = layout_chunks
        
        # 統合サマリー
        merged_result["integration_summary"] = {
            "ocr_text_chars": len(ocr_document.text) if ocr_document.text else 0,
            "ocr_coordinates_count": len(ocr_coordinates),
            "layout_chunks_count": len(layout_chunks),
            "layout_total_chunk_chars": sum(len(getattr(chunk, 'content', '')) for chunk in layout_document.chunked_document.chunks) if hasattr(layout_document, 'chunked_document') and layout_document.chunked_document else 0,
            "processing_success": True,
            "coordinate_extraction_success": len(ocr_coordinates) > 0,
            "chunking_success": len(layout_chunks) > 0
        }
        
        # 結果保存
        output_file = "hybrid_processing_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(merged_result, f, ensure_ascii=False, indent=2)
        
        print(f"✅ ハイブリッド処理結果保存: {output_file}")
        print(f"\n📊 統合結果サマリー:")
        print(f"   OCR座標数: {len(ocr_coordinates)}個")
        print(f"   OCRテキスト: {len(ocr_document.text) if ocr_document.text else 0}文字")
        print(f"   Layout チャンク: {len(layout_chunks)}個")
        print(f"   座標取得: {'✅ 成功' if len(ocr_coordinates) > 0 else '❌ 失敗'}")
        print(f"   チャンキング: {'✅ 成功' if len(layout_chunks) > 0 else '❌ 失敗'}")
        
        return merged_result

if __name__ == "__main__":
    processor = PracticalHybridProcessor()
    result = processor.process_document_complete()