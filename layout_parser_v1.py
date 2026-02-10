#!/usr/bin/env python3
"""
Layout Parser v1版 - 通常版プロセッサによる座標取得
Document AI v1 リファレンス準拠の階層でデータを取得
"""

import os
import json
import io
from PIL import Image
from datetime import datetime
from google.cloud import documentai_v1 as documentai

class LayoutParserV1:
    """Layout Parser 通常版（v1）による座標と画像取得"""
    
    def __init__(self):
        self.config = {
            "project_id": "gen-lang-client-0849825641",
            "documentai_location": "us", 
            "layout_parser_processor_id": "6af87434352688a1",
            "pdf_path": "sample.pdf"
        }
        
        # Document AI v1 クライアント初期化
        self.client = documentai.DocumentProcessorServiceClient()
    
    def get_process_options(self):
        """v1版 最小限設定（v1でサポートされている機能のみ）"""
        # v1版では基本的なProcessOptionsのみサポート
        # 複雑なオプションは使用せず、デフォルト動作に依存
        return None  # デフォルト設定でpages構造の取得を期待
    
    def analyze_document_v1(self):
        """v1版Layout Parserでの文書解析とリファレンス準拠データ取得"""
        
        print("🔍 Layout Parser v1版 テスト開始")
        print("=" * 50)
        
        results = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "api_version": "documentai_v1",
            "processor_info": {
                "type": "Layout Parser",
                "processor_id": self.config["layout_parser_processor_id"]
            },
            "pages_data": [],
            "extracted_figures": [],
            "summary": {
                "total_pages": 0,
                "total_paragraphs": 0,
                "total_lines": 0,
                "total_tokens": 0,
                "total_visual_elements": 0,
                "total_figures": 0,
                "coordinates_found": 0,
                "images_saved": 0
            }
        }
        
        try:
            # PDFファイル読み込み
            with open(self.config["pdf_path"], "rb") as f:
                pdf_content = f.read()
            
            print(f"📁 PDF読み込み: {self.config['pdf_path']} ({len(pdf_content)} bytes)")
            
            # プロセッサー設定
            processor_name = f"projects/{self.config['project_id']}/locations/{self.config['documentai_location']}/processors/{self.config['layout_parser_processor_id']}"
            
            # Document AI リクエスト（v1版）
            raw_document = documentai.RawDocument(
                content=pdf_content,
                mime_type="application/pdf"
            )
            
            process_options = self.get_process_options()
            
            if process_options:
                request = documentai.ProcessRequest(
                    name=processor_name,
                    raw_document=raw_document,
                    process_options=process_options
                )
            else:
                request = documentai.ProcessRequest(
                    name=processor_name,
                    raw_document=raw_document
                )
            
            print("🚀 Layout Parser v1 実行中...")
            result = self.client.process_document(request=request)
            document = result.document
            
            print("✅ Layout Parser v1 処理完了\\n")
            
            # 🔍 デバッグ: documentの詳細構造を調査
            print("🔍 Document 詳細調査:")
            doc_attrs = [attr for attr in dir(document) if not attr.startswith('_')]
            print(f"   利用可能属性: {doc_attrs}")
            
            # 各属性の内容確認
            for attr in ['text', 'pages', 'entities', 'paragraphs', 'tables', 'document_layout', 'images', 'content']:
                if hasattr(document, attr):
                    obj = getattr(document, attr)
                    if obj is not None:
                        if isinstance(obj, str):
                            print(f"   {attr}: {len(obj)}文字")
                            if len(obj) > 0:
                                print(f"      先頭50文字: '{obj[:50]}...'")
                        elif isinstance(obj, bytes):
                            print(f"   {attr}: {len(obj)} bytes（バイナリデータ）")
                        else:
                            try:
                                print(f"   {attr}: {len(obj)}個")
                                
                                # imagesの詳細調査
                                if attr == 'images':
                                    for img_idx, image in enumerate(obj[:3]):
                                        print(f"      画像{img_idx+1}: {type(image)}")
                                        if hasattr(image, 'content'):
                                            print(f"        content: {len(image.content)} bytes")
                                        
                            except:
                                print(f"   {attr}: オブジェクト存在")
                                
                                # document_layoutの詳細調査
                                if attr == 'document_layout':
                                    layout_attrs = [a for a in dir(obj) if not a.startswith('_')]
                                    print(f"      document_layout属性: {layout_attrs}")
                                    
                                    if hasattr(obj, 'blocks') and obj.blocks:
                                        print(f"      blocks: {len(obj.blocks)}個")
                                        
                                        # 🎯 安定版での座標情報詳細調査
                                        print(f"\\n🎯 安定版 document_layout.blocks 座標再調査:")
                                        coordinates_found_count = 0
                                        
                                        for i, block in enumerate(obj.blocks):
                                            print(f"\\nブロック{i+1}:")
                                            
                                            # テキスト内容
                                            text_content = ""
                                            if hasattr(block, 'text_block') and block.text_block:
                                                text_content = getattr(block.text_block, 'text', '')
                                                print(f"  テキスト: '{text_content[:30]}...'")
                                            
                                            # ブロックタイプ確認
                                            block_type = "unknown"
                                            for type_attr in ['type', 'block_type']:
                                                if hasattr(block, type_attr):
                                                    block_type = getattr(block, type_attr)
                                                    print(f"  タイプ: {block_type}")
                                                    break
                                            
                                            # 🔍 bounding_box の詳細調査（安定版での変化確認）
                                            print(f"  bounding_box調査:")
                                            if hasattr(block, 'bounding_box'):
                                                bbox = getattr(block, 'bounding_box')
                                                print(f"    bounding_box存在: {bbox is not None}")
                                                print(f"    bounding_boxタイプ: {type(bbox)}")
                                                
                                                if bbox is not None:
                                                    # bounding_boxの属性確認
                                                    bbox_attrs = [attr for attr in dir(bbox) if not attr.startswith('_')]
                                                    print(f"    bounding_box属性: {bbox_attrs}")
                                                    
                                                    # normalized_vertices確認
                                                    if hasattr(bbox, 'normalized_vertices'):
                                                        vertices = getattr(bbox, 'normalized_vertices')
                                                        print(f"    normalized_vertices: {vertices is not None}")
                                                        print(f"    vertices数: {len(vertices) if vertices else 0}")
                                                        
                                                        if vertices and len(vertices) >= 4:
                                                            print(f"    ✅ ブロック {i+1} ({block_type}) の座標を発見しました！")
                                                            print(f"       座標: 左上({vertices[0].x:.3f}, {vertices[0].y:.3f}) → 右下({vertices[2].x:.3f}, {vertices[2].y:.3f})")
                                                            coordinates_found_count += 1
                                                            
                                                            # 図解ブロックの場合は特に詳細表示
                                                            if str(block_type).lower() in ['figure', 'image']:
                                                                print(f"       🖼️ 図解要素発見！ テキスト: '{text_content}'")
                                                        else:
                                                            print(f"    ❌ vertices不完全: {len(vertices) if vertices else 0}個")
                                                    else:
                                                        print(f"    ❌ normalized_vertices属性なし")
                                                else:
                                                    print(f"    ❌ bounding_box: None")
                                            else:
                                                print(f"    ❌ bounding_box属性なし")
                                        
                                        print(f"\\n📊 座標発見結果: {coordinates_found_count}/{len(obj.blocks)}個のブロックで座標取得成功")
                    else:
                        print(f"   {attr}: None")
                else:
                    print(f"   {attr}: 属性なし")
            
            # 📋 1. Document基本情報
            print("\n📋 Document基本構造:")
            print(f"   全文テキスト: {len(document.text) if hasattr(document, 'text') and document.text else 0}文字")
            print(f"   pages: {len(document.pages) if hasattr(document, 'pages') and document.pages else 0}個")
            
            # ✅ pages配列の詳細調査
            if hasattr(document, 'pages'):
                pages_obj = document.pages
                print(f"\n🔍 pages配列詳細調査:")
                print(f"   pages属性型: {type(pages_obj)}")
                print(f"   pages長さ: {len(pages_obj) if pages_obj else 0}")
                print(f"   pages非None: {pages_obj is not None}")
                
                # pages配列が空でない場合の詳細調査
                if pages_obj:
                    print(f"\n   📋 各ページ要素:")
                    for i, page in enumerate(pages_obj):
                        print(f"     ページ{i+1}: {type(page)}")
                        page_attrs = [attr for attr in dir(page) if not attr.startswith('_')]
                        print(f"     ページ属性: {page_attrs}")
                else:
                    print("   ⚠️ pages配列は存在するが空です")
            else:
                print("   ❌ pages属性自体が存在しません")
            
            # 📄 2. 各ページの詳細解析（リファレンス準拠）
            if hasattr(document, 'pages') and document.pages:
                results["summary"]["total_pages"] = len(document.pages)
                
                for page_idx, page in enumerate(document.pages):
                    print(f"\\n--- ページ {page_idx + 1} 詳細解析 (リファレンス準拠) ---")
                    
                    page_data = {
                        "page_number": page_idx + 1,
                        "paragraphs": [],
                        "lines": [],
                        "tokens": [],
                        "visual_elements": [],
                        "figures": [],
                        "image_data": {}
                    }
                    
                    # 🎯 2-1. paragraphs（段落とその座標）
                    print("\\n📝 1. paragraphs（段落）解析:")
                    if hasattr(page, 'paragraphs') and page.paragraphs:
                        print(f"   paragraphs: {len(page.paragraphs)}個")
                        
                        for para_idx, paragraph in enumerate(page.paragraphs):
                            para_data = self._extract_element_data(paragraph, document.text, f"段落{para_idx+1}")
                            if para_data:
                                page_data["paragraphs"].append(para_data)
                                results["summary"]["total_paragraphs"] += 1
                                
                                print(f"     段落{para_idx+1}: '{para_data['text'][:30]}...' 座標: {para_data['coordinates_found']}個")
                    else:
                        print("   paragraphs: なし")
                    
                    # 🎯 2-2. lines（行とその座標）
                    print("\\n📏 2. lines（行）解析:")
                    if hasattr(page, 'lines') and page.lines:
                        print(f"   lines: {len(page.lines)}個")
                        
                        for line_idx, line in enumerate(page.lines[:5]):  # 最初の5行のみ表示
                            line_data = self._extract_element_data(line, document.text, f"行{line_idx+1}")
                            if line_data:
                                page_data["lines"].append(line_data)
                                results["summary"]["total_lines"] += 1
                                
                                print(f"     行{line_idx+1}: '{line_data['text'][:20]}...' 座標: {line_data['coordinates_found']}個")
                        
                        if len(page.lines) > 5:
                            print(f"     ... 他 {len(page.lines) - 5} 行")
                    else:
                        print("   lines: なし")
                    
                    # 🎯 2-3. tokens（単語とその座標）
                    print("\\n🔤 3. tokens（単語）解析:")
                    if hasattr(page, 'tokens') and page.tokens:
                        print(f"   tokens: {len(page.tokens)}個")
                        
                        for token_idx, token in enumerate(page.tokens[:10]):  # 最初の10トークンのみ
                            token_data = self._extract_element_data(token, document.text, f"トークン{token_idx+1}")
                            if token_data:
                                page_data["tokens"].append(token_data)
                                results["summary"]["total_tokens"] += 1
                                
                                print(f"     トークン{token_idx+1}: '{token_data['text']}' 座標: {token_data['coordinates_found']}個")
                        
                        if len(page.tokens) > 10:
                            print(f"     ... 他 {len(page.tokens) - 10} トークン")
                    else:
                        print("   tokens: なし")
                    
                    # 🎯 2-4. visualElements（図解・画像要素とその座標）
                    print("\\n🖼️ 4. visualElements（図解要素）解析:")
                    if hasattr(page, 'visual_elements') and page.visual_elements:
                        print(f"   visual_elements: {len(page.visual_elements)}個")
                        
                        for elem_idx, element in enumerate(page.visual_elements):
                            elem_data = {
                                "element_id": elem_idx + 1,
                                "type": getattr(element, 'type', 'unknown'),
                                "coordinates": [],
                                "coordinates_found": 0
                            }
                            
                            # 座標取得
                            if hasattr(element, 'layout') and element.layout:
                                coords = self._extract_coordinates_from_layout(element.layout)
                                if coords:
                                    elem_data["coordinates"] = coords
                                    elem_data["coordinates_found"] = len(coords)
                                    results["summary"]["coordinates_found"] += len(coords)
                            
                            page_data["visual_elements"].append(elem_data)
                            results["summary"]["total_visual_elements"] += 1
                            
                            print(f"     要素{elem_idx+1}: タイプ '{elem_data['type']}' 座標: {elem_data['coordinates_found']}個")
                            
                            # 🎯 図解（figure）要素の個別画像切り抜き
                            if elem_data['type'] == 'figure' and elem_data['coordinates_found'] > 0:
                                figure_image = self._extract_figure_image(page, elem_data, page_idx + 1, elem_idx + 1)
                                if figure_image:
                                    page_data["figures"].append(figure_image)
                                    results["extracted_figures"].append(figure_image)
                                    results["summary"]["total_figures"] += 1
                                    print(f"       ✅ 図解切り抜き成功: {figure_image['saved_path']}")
                    else:
                        print("   visual_elements: なし")
                    
                    # 🎯 2-5. image（ページ全体画像データ）
                    print("\\n📸 5. image（ページ画像）解析:")
                    if hasattr(page, 'image') and page.image:
                        image_info = self._extract_page_image(page, page_idx + 1)
                        if image_info:
                            page_data["image_data"] = image_info
                            results["summary"]["images_saved"] += 1
                            print(f"   ✅ ページ画像保存: {image_info['saved_path']}")
                            print(f"   解像度: {image_info['width']}x{image_info['height']}px")
                    else:
                        print("   image: なし")
                    
                    results["pages_data"].append(page_data)
            
            # 📊 結果サマリー
            print(f"\\n📊 v1版 Layout Parser 結果サマリー:")
            print(f"   ページ数: {results['summary']['total_pages']}")
            print(f"   段落数: {results['summary']['total_paragraphs']}")
            print(f"   行数: {results['summary']['total_lines']}")
            print(f"   トークン数: {results['summary']['total_tokens']}")
            print(f"   ビジュアル要素数: {results['summary']['total_visual_elements']}")
            print(f"   図解切り抜き数: {results['summary']['total_figures']}")
            print(f"   座標取得数: {results['summary']['coordinates_found']}")
            print(f"   画像保存数: {results['summary']['images_saved']}")
            
            # JSON保存
            output_file = "layout_parser_v1_results.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            print(f"\\n💾 結果保存完了: {output_file}")
            
        except Exception as e:
            print(f"❌ エラー発生: {e}")
            results["error"] = str(e)
        
        return results
    
    def _extract_element_data(self, element, full_text, element_name):
        """要素からテキストと座標を抽出"""
        
        element_data = {
            "text": "",
            "text_length": 0,
            "coordinates": [],
            "coordinates_found": 0
        }
        
        # テキスト取得
        if hasattr(element, 'layout') and element.layout:
            layout = element.layout
            
            # テキストアンカーからテキスト抽出
            if hasattr(layout, 'text_anchor') and layout.text_anchor:
                text_anchor = layout.text_anchor
                if hasattr(text_anchor, 'text_segments') and text_anchor.text_segments:
                    segment = text_anchor.text_segments[0]
                    start_idx = getattr(segment, 'start_index', 0)
                    end_idx = getattr(segment, 'end_index', 0)
                    if full_text:
                        element_data["text"] = full_text[start_idx:end_idx].replace("\\n", "")
                        element_data["text_length"] = len(element_data["text"])
            
            # 座標取得
            coords = self._extract_coordinates_from_layout(layout)
            if coords:
                element_data["coordinates"] = coords
                element_data["coordinates_found"] = len(coords)
        
        return element_data if element_data["text"] or element_data["coordinates_found"] > 0 else None
    
    def _extract_coordinates_from_layout(self, layout):
        """layoutから座標情報を抽出"""
        
        coordinates = []
        
        if hasattr(layout, 'bounding_poly') and layout.bounding_poly:
            bounding_poly = layout.bounding_poly
            
            if hasattr(bounding_poly, 'normalized_vertices') and bounding_poly.normalized_vertices:
                vertices = bounding_poly.normalized_vertices
                if vertices and len(vertices) >= 4:
                    coords = []
                    for vertex in vertices:
                        coords.append({
                            "x": getattr(vertex, 'x', 0),
                            "y": getattr(vertex, 'y', 0)
                        })
                    coordinates = coords
        
        return coordinates
    
    def _extract_figure_image(self, page, element_data, page_num, element_num):
        """図解要素を個別画像として切り抜き"""
        
        try:
            # ページ全体画像を取得
            if not (hasattr(page, 'image') and page.image and page.image.content):
                return None
            
            # 画像データ取得
            if isinstance(page.image.content, str):
                import base64
                image_data = base64.b64decode(page.image.content)
            else:
                image_data = page.image.content
            
            whole_image = Image.open(io.BytesIO(image_data))
            width, height = whole_image.size
            
            # 座標をピクセルに変換
            if element_data["coordinates_found"] < 4:
                return None
            
            coords = element_data["coordinates"]
            left = int(coords[0]["x"] * width)
            top = int(coords[0]["y"] * height)
            right = int(coords[2]["x"] * width)
            bottom = int(coords[2]["y"] * height)
            
            # 座標の妥当性チェック
            if left >= right or top >= bottom or left < 0 or top < 0:
                return None
            
            # 画像切り抜き
            cropped_img = whole_image.crop((left, top, right, bottom))
            
            # 保存
            figures_dir = "extracted_figures_v1"
            if not os.path.exists(figures_dir):
                os.makedirs(figures_dir)
            
            save_path = os.path.join(figures_dir, f"figure_page{page_num}_elem{element_num}.png")
            cropped_img.save(save_path)
            
            return {
                "figure_id": element_num,
                "page": page_num,
                "type": element_data["type"],
                "coordinates": {
                    "left": left,
                    "top": top,
                    "right": right,
                    "bottom": bottom
                },
                "size": {
                    "width": right - left,
                    "height": bottom - top
                },
                "saved_path": save_path
            }
            
        except Exception as e:
            print(f"       ❌ 図解切り抜きエラー: {e}")
            return None
    
    def _extract_page_image(self, page, page_num):
        """ページ全体画像を保存"""
        
        try:
            if not (hasattr(page, 'image') and page.image and page.image.content):
                return None
            
            # 画像データ取得
            if isinstance(page.image.content, str):
                import base64
                image_data = base64.b64decode(page.image.content)
            else:
                image_data = page.image.content
            
            # 画像情報
            image_info = {
                "content_size": len(image_data),
                "mime_type": getattr(page.image, 'mime_type', ''),
                "width": getattr(page.image, 'width', 0),
                "height": getattr(page.image, 'height', 0)
            }
            
            # 実際の画像サイズを取得
            whole_image = Image.open(io.BytesIO(image_data))
            actual_width, actual_height = whole_image.size
            
            image_info.update({
                "actual_width": actual_width,
                "actual_height": actual_height
            })
            
            # 保存
            images_dir = "extracted_images_v1"
            if not os.path.exists(images_dir):
                os.makedirs(images_dir)
            
            save_path = os.path.join(images_dir, f"page_{page_num}.png")
            whole_image.save(save_path)
            
            image_info["saved_path"] = save_path
            
            return image_info
            
        except Exception as e:
            print(f"   ❌ ページ画像保存エラー: {e}")
            return None

if __name__ == "__main__":
    parser = LayoutParserV1()
    result = parser.analyze_document_v1()