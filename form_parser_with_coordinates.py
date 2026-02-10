#!/usr/bin/env python3
"""
Google Cloud Document AI - Form Parser専用スクリプト
座標付きテキスト抽出、レイアウト構造解析、画像取得
Document OCRとの比較検証用
"""

import json
import base64
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import io

try:
    from google.cloud import documentai_v1 as documentai
    from google.api_core.client_options import ClientOptions
    from PIL import Image, ImageDraw
except ImportError as e:
    print(f"❌ 必要なライブラリがインストールされていません: {e}")
    print("以下のコマンドでインストールしてください:")
    print("pip install google-cloud-documentai pillow")
    exit(1)


class FormParserProcessor:
    """Form Parserプロセッサによる包括的文書解析"""
    
    def __init__(self):
        # 設定情報
        self.config = {
            "project_id": "gen-lang-client-0849825641",
            "location": "us",  # Form Parserプロセッサのロケーション
            "form_parser_processor_id": "338ea0ecd68b764b",  # Form Parserプロセッサ
            "pdf_path": "sample.pdf",
            "output_dir": "form_parser_images"
        }
        
        # Form Parser専用クライアント初期化（リージョン別エンドポイント）
        opts = ClientOptions(api_endpoint=f"{self.config['location']}-documentai.googleapis.com")
        self.client = documentai.DocumentProcessorServiceClient(client_options=opts)
        
        # 出力ディレクトリ作成
        Path(self.config["output_dir"]).mkdir(exist_ok=True)
        
        # キーワード検索用（比較用として同じキーワードを使用）
        self.chair_keywords = [
            'エッグチェア', 'アントチェア', 'スワンチェア', 'セブンチェア',
            'ベルビュー・チェア', 'アリンコチェア'
        ]
        
        # 推定エリアのオフセット設定
        self.area_offset = {
            'top': 0.1,     # 上方向10%
            'bottom': 0.1,  # 下方向10%
            'left': 0.15,   # 左方向15%
            'right': 0.15   # 右方向15%
        }
    
    def get_process_options(self):
        """Form Parser用のProcessOptions設定（基本設定のみ）"""
        # Form Parserでは基本的なOCR設定のみを使用
        return None  # デフォルト設定を使用
    
    def analyze_document_with_form_parser(self):
        """Form Parserプロセッサによる包括的文書解析"""
        
        print("🔍 Form Parser 包括的解析開始")
        print("=" * 60)
        
        results = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "processor_type": "Form Parser",
            "processor_id": self.config["form_parser_processor_id"],
            "full_text": "",
            "text_blocks": [],
            "paragraphs": [],
            "lines": [],
            "tokens": [],
            "visual_elements": [],
            "form_fields": [],
            "tables": [],
            "extracted_figures": [],
            "page_images": [],
            "summary": {
                "total_pages": 0,
                "total_blocks": 0,
                "total_paragraphs": 0,
                "total_lines": 0,
                "total_tokens": 0,
                "total_form_fields": 0,
                "total_tables": 0,
                "total_figures": 0,
                "coordinates_found": 0,
                "images_saved": 0
            }
        }
        
        try:
            # 🔹 1. PDF読み込み
            pdf_path = Path(self.config["pdf_path"])
            if not pdf_path.exists():
                raise FileNotFoundError(f"PDFファイルが見つかりません: {pdf_path}")
            
            with open(pdf_path, "rb") as pdf_file:
                pdf_content = pdf_file.read()
            
            print(f"📁 PDF読み込み: {pdf_path.name} ({len(pdf_content):,} bytes)")
            
            # 🔹 2. Form Parser実行
            processor_name = self.client.processor_path(
                self.config["project_id"], 
                self.config["location"], 
                self.config["form_parser_processor_id"]
            )
            
            raw_document = documentai.RawDocument(
                content=pdf_content, 
                mime_type="application/pdf"
            )
            
            print("🚀 Form Parser 実行中...")
            
            # ProcessOptionsを適用
            process_options = self.get_process_options()
            
            request = documentai.ProcessRequest(
                name=processor_name,
                raw_document=raw_document,
                process_options=process_options
            )
            
            # Document AI実行
            result = self.client.process_document(request=request)
            document = result.document
            
            print("✅ Form Parser 処理完了\n")
            
            # 🔹 3. 全体テキスト取得
            results["full_text"] = document.text
            print(f"📄 全テキスト取得: {len(document.text):,}文字")
            
            # 🔹 4. Form Parser特有の要素解析
            if hasattr(document, 'entities') and document.entities:
                print(f"📋 フォーム要素: {len(document.entities)}個")
                for entity_idx, entity in enumerate(document.entities):
                    field_data = self._extract_form_field(entity, document.text, entity_idx + 1)
                    if field_data:
                        results["form_fields"].append(field_data)
                        results["summary"]["total_form_fields"] += 1
            
            # 🔹 5. テーブル解析
            if hasattr(document, 'pages') and document.pages:
                for page_idx, page in enumerate(document.pages):
                    if hasattr(page, 'tables') and page.tables:
                        print(f"📊 テーブル: {len(page.tables)}個（ページ{page_idx + 1}）")
                        for table_idx, table in enumerate(page.tables):
                            table_data = self._extract_table_data(table, document.text, page_idx + 1, table_idx + 1)
                            if table_data:
                                results["tables"].append(table_data)
                                results["summary"]["total_tables"] += 1
            
            # 🔹 6. ページ別詳細解析
            if hasattr(document, 'pages') and document.pages:
                results["summary"]["total_pages"] = len(document.pages)
                print(f"📋 ページ数: {len(document.pages)}個\n")
                
                for page_idx, page in enumerate(document.pages):
                    print(f"--- ページ {page_idx + 1} 解析（Form Parser）---")
                    
                    # 🎯 6-1. テキストブロックと座標抽出
                    if hasattr(page, 'blocks') and page.blocks:
                        print(f"📝 テキストブロック: {len(page.blocks)}個")
                        
                        for block_idx, block in enumerate(page.blocks):
                            block_data = self._extract_text_block_with_coordinates(
                                block, document.text, page_idx + 1, block_idx + 1
                            )
                            if block_data:
                                results["text_blocks"].append(block_data)
                                results["summary"]["total_blocks"] += 1
                                if block_data["coordinates"]:
                                    results["summary"]["coordinates_found"] += 1
                                
                                print(f"  ブロック{block_idx + 1}: '{block_data['text'][:30]}...' "
                                      f"座標: {'✅' if block_data['coordinates'] else '❌'}")
                    
                    # 🎯 6-2. 段落解析
                    if hasattr(page, 'paragraphs') and page.paragraphs:
                        print(f"📝 段落: {len(page.paragraphs)}個")
                        for para_idx, paragraph in enumerate(page.paragraphs):
                            para_data = self._extract_text_element_with_coordinates(
                                paragraph, document.text, page_idx + 1, para_idx + 1, "paragraph"
                            )
                            if para_data:
                                results["paragraphs"].append(para_data)
                                results["summary"]["total_paragraphs"] += 1
                    
                    # 🎯 6-3. 行解析
                    if hasattr(page, 'lines') and page.lines:
                        print(f"📏 行: {len(page.lines)}個")
                        for line_idx, line in enumerate(page.lines[:10]):  # 最初の10行のみ表示
                            line_data = self._extract_text_element_with_coordinates(
                                line, document.text, page_idx + 1, line_idx + 1, "line"
                            )
                            if line_data:
                                results["lines"].append(line_data)
                                results["summary"]["total_lines"] += 1
                        
                        if len(page.lines) > 10:
                            print(f"     ... 他 {len(page.lines) - 10} 行")
                    
                    # 🎯 6-4. トークン解析
                    if hasattr(page, 'tokens') and page.tokens:
                        print(f"🔤 トークン: {len(page.tokens)}個")
                        for token_idx, token in enumerate(page.tokens[:15]):  # 最初の15トークンのみ
                            token_data = self._extract_text_element_with_coordinates(
                                token, document.text, page_idx + 1, token_idx + 1, "token"
                            )
                            if token_data:
                                results["tokens"].append(token_data)
                                results["summary"]["total_tokens"] += 1
                        
                        if len(page.tokens) > 15:
                            print(f"     ... 他 {len(page.tokens) - 15} トークン")
                    
                    # 🎯 6-5. 視覚的要素と座標抽出（詳細調査付き）
                    print(f"\n🔍 visual_elements 詳細調査（Form Parser）:")
                    
                    if hasattr(page, 'visual_elements'):
                        visual_elements = page.visual_elements
                        print(f"   visual_elements属性: 存在")
                        print(f"   visual_elements型: {type(visual_elements)}")
                        print(f"   visual_elements長さ: {len(visual_elements) if visual_elements else 0}")
                        
                        if visual_elements and len(visual_elements) > 0:
                            print(f"🖼️ 視覚的要素: {len(visual_elements)}個")
                            
                            for elem_idx, element in enumerate(visual_elements):
                                elem_data = self._extract_visual_element_with_coordinates(
                                    element, page_idx + 1, elem_idx + 1
                                )
                                if elem_data:
                                    results["visual_elements"].append(elem_data)
                                    
                                    if elem_data["type"] == "figure":
                                        results["summary"]["total_figures"] += 1
                                        print(f"     ✅ 図表として認識: '{elem_data['type']}'")
                                    else:
                                        print(f"     📊 その他要素: '{elem_data['type']}'")
                        else:
                            print(f"   ⚠️ visual_elements配列は存在するが空です")
                            
                            # 🎯 キーワード検索による推定画像エリア抽出
                            print(f"\n🎯 キーワード検索: 椅子関連テキストから画像エリアを推定")
                            self._extract_estimated_image_areas_by_keywords(page, results, page_idx + 1, document.text)
                    else:
                        print(f"   ❌ visual_elements属性が存在しません")
                    
                    # 🎯 6-6. ページ画像保存
                    if hasattr(page, 'image') and page.image:
                        page_image_info = self._save_page_image(page, page_idx + 1)
                        if page_image_info:
                            results["page_images"].append(page_image_info)
                            results["summary"]["images_saved"] += 1
                            print(f"💾 ページ画像保存: {page_image_info['filename']}")
                    
                    print()  # 空行
            
            # 🔹 7. 図表の個別切り抜き実行
            print("🔄 図表切り抜き処理開始...")
            self._extract_figure_images(results)
            
            # 🔹 8. 結果サマリー表示
            self._display_summary(results)
            
            # 🔹 9. 結果をJSONファイルに保存
            output_file = f"form_parser_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            print(f"💾 結果保存完了: {output_file}")
            
            return results
            
        except Exception as e:
            print(f"❌ エラーが発生しました: {e}")
            return None
    
    def _extract_form_field(self, entity, full_text: str, field_num: int) -> Dict[str, Any]:
        """フォームフィールドデータを抽出"""
        
        field_data = {
            "field_id": field_num,
            "type": str(entity.type_) if hasattr(entity, 'type_') else "unknown",
            "mention_text": "",
            "normalized_value": "",
            "confidence": float(entity.confidence) if hasattr(entity, 'confidence') else 0.0,
            "coordinates": [],
            "bounding_box": {}
        }
        
        try:
            # メンションテキスト取得
            if hasattr(entity, 'mention_text') and entity.mention_text:
                field_data["mention_text"] = entity.mention_text
            
            # 正規化値取得
            if hasattr(entity, 'normalized_value') and entity.normalized_value:
                if hasattr(entity.normalized_value, 'text'):
                    field_data["normalized_value"] = entity.normalized_value.text
            
            # 座標情報取得（page_anchorから）
            if hasattr(entity, 'page_anchor') and entity.page_anchor:
                page_refs = entity.page_anchor.page_refs
                if page_refs and len(page_refs) > 0:
                    page_ref = page_refs[0]
                    if hasattr(page_ref, 'bounding_poly'):
                        bounding_poly = page_ref.bounding_poly
                        if hasattr(bounding_poly, 'normalized_vertices'):
                            coordinates = []
                            for vertex in bounding_poly.normalized_vertices:
                                if hasattr(vertex, 'x') and hasattr(vertex, 'y'):
                                    coordinates.append({
                                        "x": float(vertex.x),
                                        "y": float(vertex.y)
                                    })
                            
                            if len(coordinates) >= 4:
                                field_data["coordinates"] = coordinates
                                field_data["bounding_box"] = {
                                    "left": coordinates[0]["x"],
                                    "top": coordinates[0]["y"],
                                    "right": coordinates[2]["x"],
                                    "bottom": coordinates[2]["y"],
                                    "width": coordinates[2]["x"] - coordinates[0]["x"],
                                    "height": coordinates[2]["y"] - coordinates[0]["y"]
                                }
            
            return field_data if field_data["mention_text"] or field_data["normalized_value"] else None
            
        except Exception as e:
            print(f"⚠️ フィールド{field_num}の処理でエラー: {e}")
            return None
    
    def _extract_table_data(self, table, full_text: str, page_num: int, table_num: int) -> Dict[str, Any]:
        """テーブルデータを抽出"""
        
        table_data = {
            "page": page_num,
            "table_id": table_num,
            "rows": [],
            "coordinates": [],
            "bounding_box": {}
        }
        
        try:
            # テーブルの座標取得
            if hasattr(table, 'layout') and hasattr(table.layout, 'bounding_poly'):
                bounding_poly = table.layout.bounding_poly
                if hasattr(bounding_poly, 'normalized_vertices'):
                    coordinates = []
                    for vertex in bounding_poly.normalized_vertices:
                        if hasattr(vertex, 'x') and hasattr(vertex, 'y'):
                            coordinates.append({
                                "x": float(vertex.x),
                                "y": float(vertex.y)
                            })
                    
                    if len(coordinates) >= 4:
                        table_data["coordinates"] = coordinates
                        table_data["bounding_box"] = {
                            "left": coordinates[0]["x"],
                            "top": coordinates[0]["y"],
                            "right": coordinates[2]["x"],
                            "bottom": coordinates[2]["y"],
                            "width": coordinates[2]["x"] - coordinates[0]["x"],
                            "height": coordinates[2]["y"] - coordinates[0]["y"]
                        }
            
            # テーブル行データ取得
            if hasattr(table, 'header_rows') and table.header_rows:
                for row_idx, row in enumerate(table.header_rows):
                    row_data = self._extract_table_row_data(row, full_text, f"header_{row_idx}")
                    if row_data:
                        table_data["rows"].append(row_data)
            
            if hasattr(table, 'body_rows') and table.body_rows:
                for row_idx, row in enumerate(table.body_rows):
                    row_data = self._extract_table_row_data(row, full_text, f"body_{row_idx}")
                    if row_data:
                        table_data["rows"].append(row_data)
            
            return table_data if table_data["rows"] else None
            
        except Exception as e:
            print(f"⚠️ テーブル{table_num}の処理でエラー: {e}")
            return None
    
    def _extract_table_row_data(self, row, full_text: str, row_id: str) -> Dict[str, Any]:
        """テーブル行データを抽出"""
        
        row_data = {
            "row_id": row_id,
            "cells": []
        }
        
        try:
            if hasattr(row, 'cells') and row.cells:
                for cell_idx, cell in enumerate(row.cells):
                    cell_text = ""
                    if hasattr(cell, 'layout') and hasattr(cell.layout, 'text_anchor'):
                        text_anchor = cell.layout.text_anchor
                        if hasattr(text_anchor, 'text_segments'):
                            for segment in text_anchor.text_segments:
                                start_idx = int(segment.start_index) if hasattr(segment, 'start_index') else 0
                                end_idx = int(segment.end_index) if hasattr(segment, 'end_index') else 0
                                cell_text += full_text[start_idx:end_idx]
                    
                    row_data["cells"].append({
                        "cell_id": cell_idx,
                        "text": cell_text.strip()
                    })
            
            return row_data if row_data["cells"] else None
            
        except Exception as e:
            print(f"⚠️ 行{row_id}の処理でエラー: {e}")
            return None
    
    def _extract_text_block_with_coordinates(self, block, full_text: str, page_num: int, block_num: int) -> Dict[str, Any]:
        """テキストブロックから座標付きデータを抽出（Document OCRと同じロジック）"""
        
        block_data = {
            "page": page_num,
            "block_id": block_num,
            "text": "",
            "coordinates": [],
            "bounding_box": {}
        }
        
        try:
            # テキスト内容取得
            if hasattr(block, 'layout') and hasattr(block.layout, 'text_anchor'):
                text_anchor = block.layout.text_anchor
                if hasattr(text_anchor, 'text_segments'):
                    for segment in text_anchor.text_segments:
                        start_idx = int(segment.start_index) if hasattr(segment, 'start_index') else 0
                        end_idx = int(segment.end_index) if hasattr(segment, 'end_index') else 0
                        block_data["text"] += full_text[start_idx:end_idx]
            
            # 座標情報取得
            if hasattr(block, 'layout') and hasattr(block.layout, 'bounding_poly'):
                bounding_poly = block.layout.bounding_poly
                if hasattr(bounding_poly, 'normalized_vertices'):
                    coordinates = []
                    for vertex in bounding_poly.normalized_vertices:
                        if hasattr(vertex, 'x') and hasattr(vertex, 'y'):
                            coordinates.append({
                                "x": float(vertex.x),
                                "y": float(vertex.y)
                            })
                    
                    if len(coordinates) >= 4:
                        block_data["coordinates"] = coordinates
                        block_data["bounding_box"] = {
                            "left": coordinates[0]["x"],
                            "top": coordinates[0]["y"], 
                            "right": coordinates[2]["x"],
                            "bottom": coordinates[2]["y"],
                            "width": coordinates[2]["x"] - coordinates[0]["x"],
                            "height": coordinates[2]["y"] - coordinates[0]["y"]
                        }
            
            return block_data if block_data["text"].strip() else None
            
        except Exception as e:
            print(f"⚠️ ブロック{block_num}の処理でエラー: {e}")
            return None
    
    def _extract_text_element_with_coordinates(self, element, full_text: str, page_num: int, elem_num: int, elem_type: str) -> Dict[str, Any]:
        """汎用テキスト要素から座標付きデータを抽出"""
        
        elem_data = {
            "page": page_num,
            "element_id": elem_num,
            "element_type": elem_type,
            "text": "",
            "coordinates": [],
            "bounding_box": {}
        }
        
        try:
            # テキスト内容取得
            if hasattr(element, 'layout') and hasattr(element.layout, 'text_anchor'):
                text_anchor = element.layout.text_anchor
                if hasattr(text_anchor, 'text_segments'):
                    for segment in text_anchor.text_segments:
                        start_idx = int(segment.start_index) if hasattr(segment, 'start_index') else 0
                        end_idx = int(segment.end_index) if hasattr(segment, 'end_index') else 0
                        elem_data["text"] += full_text[start_idx:end_idx]
            
            # 座標情報取得
            if hasattr(element, 'layout') and hasattr(element.layout, 'bounding_poly'):
                bounding_poly = element.layout.bounding_poly
                if hasattr(bounding_poly, 'normalized_vertices'):
                    coordinates = []
                    for vertex in bounding_poly.normalized_vertices:
                        if hasattr(vertex, 'x') and hasattr(vertex, 'y'):
                            coordinates.append({
                                "x": float(vertex.x),
                                "y": float(vertex.y)
                            })
                    
                    if len(coordinates) >= 4:
                        elem_data["coordinates"] = coordinates
                        elem_data["bounding_box"] = {
                            "left": coordinates[0]["x"],
                            "top": coordinates[0]["y"],
                            "right": coordinates[2]["x"],
                            "bottom": coordinates[2]["y"],
                            "width": coordinates[2]["x"] - coordinates[0]["x"],
                            "height": coordinates[2]["y"] - coordinates[0]["y"]
                        }
            
            return elem_data if elem_data["text"].strip() else None
            
        except Exception as e:
            print(f"⚠️ {elem_type}{elem_num}の処理でエラー: {e}")
            return None
    
    def _extract_visual_element_with_coordinates(self, element, page_num: int, elem_num: int) -> Dict[str, Any]:
        """視覚的要素から座標付きデータを抽出（Document OCRと同じロジック）"""
        
        elem_data = {
            "page": page_num,
            "element_id": elem_num,
            "type": "unknown",
            "coordinates": [],
            "bounding_box": {}
        }
        
        try:
            # 要素タイプ取得
            if hasattr(element, 'type'):
                elem_data["type"] = str(element.type).lower()
            
            # 座標情報取得
            if hasattr(element, 'layout') and hasattr(element.layout, 'bounding_poly'):
                bounding_poly = element.layout.bounding_poly
                if hasattr(bounding_poly, 'normalized_vertices'):
                    coordinates = []
                    for vertex in bounding_poly.normalized_vertices:
                        if hasattr(vertex, 'x') and hasattr(vertex, 'y'):
                            coordinates.append({
                                "x": float(vertex.x),
                                "y": float(vertex.y)
                            })
                    
                    if len(coordinates) >= 4:
                        elem_data["coordinates"] = coordinates
                        elem_data["bounding_box"] = {
                            "left": coordinates[0]["x"],
                            "top": coordinates[0]["y"],
                            "right": coordinates[2]["x"], 
                            "bottom": coordinates[2]["y"],
                            "width": coordinates[2]["x"] - coordinates[0]["x"],
                            "height": coordinates[2]["y"] - coordinates[0]["y"]
                        }
            
            return elem_data if elem_data["coordinates"] else None
            
        except Exception as e:
            print(f"⚠️ 視覚要素{elem_num}の処理でエラー: {e}")
            return None
    
    def _extract_estimated_image_areas_by_keywords(self, page, results: Dict[str, Any], page_num: int, full_text: str):
        """キーワード検索による推定画像エリア抽出（Document OCRと同じロジック）"""
        
        try:
            if not hasattr(page, 'blocks') or not page.blocks:
                print(f"   blocks属性なし")
                return
            
            keyword_blocks_found = 0
            
            for keyword in self.chair_keywords:
                print(f"\n   🔍 キーワード検索: '{keyword}'")
                
                # キーワードを含むブロックを検索
                matching_blocks = []
                
                for block_idx, block in enumerate(page.blocks):
                    # ブロックのテキスト内容を取得
                    block_text = ""
                    if (hasattr(block, 'layout') and 
                        hasattr(block.layout, 'text_anchor') and
                        block.layout.text_anchor.text_segments):
                        
                        for segment in block.layout.text_anchor.text_segments:
                            start_idx = int(segment.start_index) if hasattr(segment, 'start_index') else 0
                            end_idx = int(segment.end_index) if hasattr(segment, 'end_index') else 0
                            block_text += full_text[start_idx:end_idx]
                    
                    # キーワードマッチング
                    if keyword in block_text:
                        # 座標情報を取得
                        if (hasattr(block, 'layout') and 
                            hasattr(block.layout, 'bounding_poly') and
                            hasattr(block.layout.bounding_poly, 'normalized_vertices')):
                            
                            vertices = block.layout.bounding_poly.normalized_vertices
                            if len(vertices) >= 4:
                                block_coords = {
                                    'block_idx': block_idx + 1,
                                    'text': block_text.strip(),
                                    'keyword': keyword,
                                    'left': float(vertices[0].x),
                                    'top': float(vertices[0].y),
                                    'right': float(vertices[2].x),
                                    'bottom': float(vertices[2].y)
                                }
                                matching_blocks.append(block_coords)
                                print(f"     ✅ ブロック{block_idx + 1}で発見: '{block_text[:30]}...'")
                
                # マッチしたブロックがある場合、推定画像エリアを作成
                if matching_blocks:
                    for i, match in enumerate(matching_blocks):
                        estimated_area = self._create_estimated_image_area(match, keyword, i + 1)
                        
                        if estimated_area:
                            results["visual_elements"].append(estimated_area)
                            results["summary"]["total_figures"] += 1
                            keyword_blocks_found += 1
                            
                            print(f"     📊 推定画像エリア作成: {estimated_area['estimated_type']}")
                            print(f"        座標範囲: ({estimated_area['bounding_box']['left']:.3f}, {estimated_area['bounding_box']['top']:.3f}) → ({estimated_area['bounding_box']['right']:.3f}, {estimated_area['bounding_box']['bottom']:.3f})")
                else:
                    print(f"     ❌ '{keyword}' を含むブロックが見つかりません")
            
            if keyword_blocks_found > 0:
                print(f"\n   🎯 キーワード検索結果: {keyword_blocks_found}個の推定画像エリアを作成")
            else:
                print(f"\n   ⚠️ キーワード検索でも推定エリアは見つかりませんでした")
                
        except Exception as e:
            print(f"   ⚠️ キーワード検索でエラー: {e}")
    
    def _create_estimated_image_area(self, text_block: Dict, keyword: str, instance_num: int) -> Optional[Dict[str, Any]]:
        """テキストブロック座標から推定画像エリアを作成（Document OCRと同じロジック）"""
        
        try:
            # テキストブロックの中心座標を計算
            text_center_x = (text_block['left'] + text_block['right']) / 2
            text_center_y = (text_block['top'] + text_block['bottom']) / 2
            
            # オフセットを適用して推定エリアを計算
            estimated_left = max(0.0, text_center_x - self.area_offset['left'])
            estimated_right = min(1.0, text_center_x + self.area_offset['right'])
            estimated_top = max(0.0, text_center_y - self.area_offset['top'])
            estimated_bottom = min(1.0, text_center_y + self.area_offset['bottom'])
            
            # 推定画像エリアデータを作成
            estimated_area = {
                "page": 1,
                "element_id": f"keyword_{keyword}_{instance_num}",
                "type": "estimated_figure",
                "source": "keyword_search",
                "estimated_type": f"{keyword}_area",
                "text_reference": {
                    "block_idx": text_block['block_idx'],
                    "keyword": keyword,
                    "text_content": text_block['text']
                },
                "coordinates": [
                    {"x": estimated_left, "y": estimated_top},
                    {"x": estimated_right, "y": estimated_top},
                    {"x": estimated_right, "y": estimated_bottom},
                    {"x": estimated_left, "y": estimated_bottom}
                ],
                "bounding_box": {
                    "left": estimated_left,
                    "top": estimated_top,
                    "right": estimated_right,
                    "bottom": estimated_bottom,
                    "width": estimated_right - estimated_left,
                    "height": estimated_bottom - estimated_top
                }
            }
            
            return estimated_area
            
        except Exception as e:
            print(f"   ⚠️ 推定エリア作成でエラー: {e}")
            return None
    
    def _save_page_image(self, page, page_num: int) -> Optional[Dict[str, Any]]:
        """ページ画像をBase64からデコードして保存"""
        
        try:
            if hasattr(page, 'image') and hasattr(page.image, 'content'):
                # Base64デコード
                image_bytes = page.image.content
                image = Image.open(io.BytesIO(image_bytes))
                
                # 画像保存
                filename = f"form_parser_page_{page_num:02d}.png"
                filepath = Path(self.config["output_dir"]) / filename
                image.save(filepath, "PNG")
                
                return {
                    "page": page_num,
                    "filename": filename,
                    "filepath": str(filepath),
                    "width": image.width,
                    "height": image.height,
                    "size_mb": round(len(image_bytes) / 1024 / 1024, 2)
                }
            
            return None
            
        except Exception as e:
            print(f"⚠️ ページ{page_num}画像保存でエラー: {e}")
            return None
    
    def _extract_figure_images(self, results: Dict[str, Any]):
        """座標情報を使用してページ画像から図表を切り抜き"""
        
        extracted_count = 0
        
        try:
            # 図表要素のみをフィルタリング（推定図表も含む）
            figure_elements = [elem for elem in results["visual_elements"] 
                             if elem["type"] in ["figure", "estimated_figure", "potential_image"]]
            
            if not figure_elements:
                print("📊 切り抜き対象の図表が見つかりませんでした")
                return
            
            print(f"📊 {len(figure_elements)}個の図表切り抜きを開始...")
            print("   対象タイプ:", [elem["type"] for elem in figure_elements])
            
            # ページ画像と図表の対応付け
            for figure in figure_elements:
                page_num = figure["page"]
                
                # 対応するページ画像を検索
                page_image = next(
                    (img for img in results["page_images"] if img["page"] == page_num), 
                    None
                )
                
                if not page_image:
                    print(f"⚠️ ページ{page_num}の画像が見つかりません")
                    continue
                
                # 画像切り抜き実行
                cropped_info = self._crop_figure_from_page(figure, page_image)
                if cropped_info:
                    results["extracted_figures"].append(cropped_info)
                    extracted_count += 1
                    print(f"✅ 図表切り抜き成功: {cropped_info['filename']}")
            
            results["summary"]["total_figures"] = extracted_count
            print(f"🎯 図表切り抜き完了: {extracted_count}個")
            
        except Exception as e:
            print(f"❌ 図表切り抜き処理でエラー: {e}")
    
    def _crop_figure_from_page(self, figure: Dict[str, Any], page_image: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """ページ画像から指定座標の図表を切り抜き"""
        
        try:
            # ページ画像を開く
            page_img = Image.open(page_image["filepath"])
            page_width, page_height = page_img.size
            
            # 正規化座標を実際のピクセル座標に変換
            bbox = figure["bounding_box"]
            left = int(bbox["left"] * page_width)
            top = int(bbox["top"] * page_height)
            right = int(bbox["right"] * page_width)
            bottom = int(bbox["bottom"] * page_height)
            
            # 切り抜き実行
            cropped_img = page_img.crop((left, top, right, bottom))
            
            # 保存ファイル名を生成（Form Parser用に変更）
            if figure.get('source') == 'keyword_search':
                filename = f"form_parser_estimated_{figure['estimated_type']}_page{figure['page']:02d}.png"
            else:
                filename = f"form_parser_figure_page{figure['page']:02d}_elem{figure['element_id']}.png"
            
            filepath = Path(self.config["output_dir"]) / filename
            cropped_img.save(filepath, "PNG")
            
            return {
                "page": figure["page"],
                "element_id": figure["element_id"],
                "filename": filename,
                "filepath": str(filepath),
                "original_coordinates": figure["coordinates"],
                "pixel_coordinates": {
                    "left": left,
                    "top": top,
                    "right": right,
                    "bottom": bottom
                },
                "width": right - left,
                "height": bottom - top
            }
            
        except Exception as e:
            print(f"⚠️ 図表切り抜きでエラー: {e}")
            return None
    
    def _display_summary(self, results: Dict[str, Any]):
        """結果サマリーを表示"""
        
        print("\n" + "=" * 60)
        print("📊 Form Parser 解析結果サマリー")
        print("=" * 60)
        
        summary = results["summary"]
        
        print(f"📄 全文字数: {len(results['full_text']):,}文字")
        print(f"📋 ページ数: {summary['total_pages']}個")
        print(f"📝 テキストブロック: {summary['total_blocks']}個")
        print(f"📝 段落: {summary['total_paragraphs']}個")
        print(f"📏 行: {summary['total_lines']}個")
        print(f"🔤 トークン: {summary['total_tokens']}個")
        print(f"📋 フォームフィールド: {summary['total_form_fields']}個")
        print(f"📊 テーブル: {summary['total_tables']}個")
        print(f"🎯 座標取得成功: {summary['coordinates_found']}個")
        print(f"🖼️ 図表要素: {summary['total_figures']}個")
        print(f"💾 画像保存: {summary['images_saved']}個")
        
        if results["extracted_figures"]:
            print(f"\n✅ 切り抜き成功した図表:")
            for figure in results["extracted_figures"]:
                print(f"  - {figure['filename']} ({figure['width']}x{figure['height']}px)")


def main():
    """メイン実行関数"""
    print("🚀 Google Cloud Document AI - Form Parser")
    print("包括的文書解析スクリプト（Document OCR比較用）")
    print("=" * 60)
    
    processor = FormParserProcessor()
    results = processor.analyze_document_with_form_parser()
    
    if results:
        print("\n🎉 処理が正常に完了しました！")
        print(f"📁 出力ディレクトリ: {processor.config['output_dir']}")
        print(f"📊 Document OCRと比較してご確認ください")
    else:
        print("\n❌ 処理中にエラーが発生しました")


if __name__ == "__main__":
    main()